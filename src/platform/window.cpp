#include "window.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#ifdef _WIN32
#include <GL/glext.h>
#endif // _WIN32

namespace tfx::platform {
namespace {
// Menus use GLFW's user pointer for their own input state.
std::unordered_map<GLFWwindow*,window*> window_instances;
struct display_area { vec2<int> position; vec2<int> size; };
display_area viewport(int const width, int const height) {
  double const available{std::min(width / static_cast<double>(render::display_width),height / static_cast<double>(render::display_height))};
  double const fit{available >= 1 ? std::floor(available) : available};
  vec2<int> const fitted{std::max(1,static_cast<int>(render::display_width * fit)),std::max(1,static_cast<int>(render::display_height * fit))};
  return {
    .position{(width - fitted.x) / 2,(height - fitted.y) / 2},
    .size{vec2<int>{fitted}},
  };
}
} // anonymous namespace


glfw_runtime::glfw_runtime() {
  glfwSetErrorCallback([](int const code, char const *const message){ std::cerr << "ERROR: GLFW " << code << ": " << message << std::endl; });
  if(!glfwInit()) throw std::runtime_error{"GLFW could not initialise a desktop display"};
}
glfw_runtime::~glfw_runtime() {
  glfwTerminate();
}

window::window(unsigned int const scale, bool const fullscreen) : handle{nullptr, glfwDestroyWindow} {
  /// Match Darker's floating-window sizing and nearest-neighbour presentation; only the final CPU image uses OpenGL
  bool const automatic{scale == 0}, compositor_sizing{automatic && !fullscreen && glfwGetPlatform() == GLFW_PLATFORM_WAYLAND};
  glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,2);
  glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,1);
  glfwWindowHint(GLFW_VISIBLE,GLFW_FALSE);
  glfwWindowHint(GLFW_AUTO_ICONIFY,GLFW_FALSE);
  glfwWindowHint(GLFW_MAXIMIZED,compositor_sizing ? GLFW_TRUE : GLFW_FALSE);
  auto const initial_scale{static_cast<int>(scale ? scale : 2)};
  handle.reset(glfwCreateWindow(render::display_width * initial_scale,render::display_height * initial_scale,"TFX C++ — scene inspection",nullptr,nullptr));
  if(!handle) throw std::runtime_error{"cannot create the TFX window"};
  if(automatic && glfwGetPlatform() != GLFW_PLATFORM_WAYLAND) {
    if(auto *monitor{glfwGetPrimaryMonitor()}) {
      int x{0}, y{0}, width{0}, height{0}, left{0}, top{0}, right{0}, bottom{0};
      glfwGetMonitorWorkarea(monitor,&x,&y,&width,&height);
      glfwGetWindowFrameSize(handle.get(),&left,&top,&right,&bottom);
      int const fit{std::max(1,std::min((width - left - right) / render::display_width,(height - top - bottom) / render::display_height))};
      glfwSetWindowSize(handle.get(),render::display_width * fit,render::display_height * fit);
      glfwSetWindowPos(handle.get(),x + left + (width - left - right - render::display_width * fit) / 2,y + top + (height - top - bottom - render::display_height * fit) / 2);
    }
  }
  // Wayland creates the shell role when shown; it needs that role before fullscreen.
  if(fullscreen && glfwGetPlatform() != GLFW_PLATFORM_WAYLAND) set_fullscreen(true);
  glfwShowWindow(handle.get());
  if(fullscreen && glfwGetPlatform() == GLFW_PLATFORM_WAYLAND) set_fullscreen(true);
  if(compositor_sizing) {
    int width{0}, height{0};
    glfwGetWindowSize(handle.get(),&width,&height);
    glfwRestoreWindow(handle.get());
    auto const deadline{glfwGetTime() + 1};
    while(glfwGetWindowAttrib(handle.get(),GLFW_MAXIMIZED) && glfwGetTime() < deadline) glfwWaitEventsTimeout(.01);
    int const fit{std::max(1,std::min(width / render::display_width,height / render::display_height))};
    glfwSetWindowSize(handle.get(),render::display_width * fit,render::display_height * fit);
  }
  glfwMakeContextCurrent(handle.get());
  glfwSwapInterval(1);
  glGenTextures(1,&texture);
  glBindTexture(GL_TEXTURE_2D,texture);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
  glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,render::screen_width,render::screen_height,0,GL_RGBA,GL_UNSIGNED_BYTE,nullptr);
  if(glGetError() != GL_NO_ERROR) throw std::runtime_error{"cannot allocate the TFX display texture"};
  glDisable(GL_DITHER);
  glEnable(GL_TEXTURE_2D);
  glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_REPLACE);
  window_instances.emplace(handle.get(),this);
  glfwSetKeyCallback(handle.get(),dispatch_key);
  glfwSetWindowFocusCallback(handle.get(),[](GLFWwindow *const target, int const focused){
    if(!focused) glfwSetInputMode(target,GLFW_CURSOR,GLFW_CURSOR_NORMAL);
  });
}

window::~window() {
  window_instances.erase(handle.get());
  glDeleteTextures(1,&texture);
}
GLFWwindow *window::get() const {
  return handle.get();
}
bool window::focused() const {
  return glfwGetWindowAttrib(handle.get(),GLFW_FOCUSED) == GLFW_TRUE;
}
GLFWkeyfun window::set_key_callback(GLFWkeyfun const callback) {
  return std::exchange(key_callback,callback);
}
bool window::key_down(int const key) const {
  if(key == GLFW_KEY_ENTER && fullscreen_keys[0]) return false;
  if(key == GLFW_KEY_KP_ENTER && fullscreen_keys[1]) return false;
  return glfwGetKey(handle.get(),key) == GLFW_PRESS;
}
void window::dispatch_key(GLFWwindow *const host, int const key, int const scan, int const action, int const modifiers) {
  auto &self{*window_instances.at(host)};
  if(key == GLFW_KEY_ENTER || key == GLFW_KEY_KP_ENTER) {
    auto &consumed{self.fullscreen_keys[key == GLFW_KEY_ENTER ? 0u : 1u]};
    if(action == GLFW_PRESS && (modifiers & GLFW_MOD_ALT)) {
      consumed = true;
      self.set_fullscreen(glfwGetWindowMonitor(host) == nullptr);
      return;
    }
    if(consumed) {
      if(action == GLFW_RELEASE) consumed = false;
      return;
    }
  }
  if(self.key_callback) self.key_callback(host,key,scan,action,modifiers);
}
void window::set_fullscreen(bool const enabled) {
  auto *const host{handle.get()};
  if(enabled == (glfwGetWindowMonitor(host) != nullptr)) return;
  if(!enabled) {
    glfwSetWindowMonitor(host,nullptr,windowed_position.x,windowed_position.y,windowed_size.x,windowed_size.y,GLFW_DONT_CARE);
    if(windowed_maximized) glfwMaximizeWindow(host);
    return;
  }
  auto *monitor{glfwGetPrimaryMonitor()};
  glfwGetWindowSize(host,&windowed_size.x,&windowed_size.y);
  windowed_maximized = glfwGetWindowAttrib(host,GLFW_MAXIMIZED) == GLFW_TRUE;
  if(glfwGetPlatform() != GLFW_PLATFORM_WAYLAND) {
    glfwGetWindowPos(host,&windowed_position.x,&windowed_position.y);
    int count{0};
    auto **monitors{glfwGetMonitors(&count)};
    int64_t best_overlap{0};
    for(int i{0}; i < count; ++i) {
      auto const *mode{glfwGetVideoMode(monitors[i])};
      if(!mode) continue;
      int x{0}, y{0};
      glfwGetMonitorPos(monitors[i],&x,&y);
      auto const width{std::max(0,std::min(windowed_position.x + windowed_size.x,x + mode->width) - std::max(windowed_position.x,x))};
      auto const height{std::max(0,std::min(windowed_position.y + windowed_size.y,y + mode->height) - std::max(windowed_position.y,y))};
      int64_t const overlap{static_cast<int64_t>(width) * height};
      if(overlap > best_overlap) { monitor = monitors[i];best_overlap = overlap; }
    }
  }
  if(monitor) if(auto const *mode{glfwGetVideoMode(monitor)})
    glfwSetWindowMonitor(host,monitor,0,0,mode->width,mode->height,mode->refreshRate);
}
bool window::poll() {
  glfwPollEvents();
  return !glfwWindowShouldClose(handle.get());
}
std::optional<vec2d> window::cursor_coordinates() const {
  int width{0}, height{0}, framebuffer_width{0}, framebuffer_height{0};
  glfwGetWindowSize(handle.get(),&width,&height);
  glfwGetFramebufferSize(handle.get(),&framebuffer_width,&framebuffer_height);
  if(width <= 0 || height <= 0 || framebuffer_width <= 0 || framebuffer_height <= 0) return {};
  double x{0}, y{0};
  glfwGetCursorPos(handle.get(),&x,&y);
  auto const area{viewport(framebuffer_width,framebuffer_height)};
  x = x * framebuffer_width / width - area.position.x;
  y = y * framebuffer_height / height - (framebuffer_height - area.position.y - area.size.y);
  return vec2d{x * render::screen_width / area.size.x,y * render::screen_height / area.size.y};
}
std::optional<vec2<int16_t>> window::cursor_position() const {
  auto const position{cursor_coordinates()};
  if(!position || position->x < 0 || position->y < 0 || position->x >= render::screen_width || position->y >= render::screen_height) return {};
  return vec2<int16_t>{*position};
}
void window::title(std::string const &text) {
  glfwSetWindowTitle(handle.get(),text.c_str());
}
void window::present(std::span<render::rgba_pixel const> const pixels) {
  int width{0}, height{0};
  glfwGetFramebufferSize(handle.get(),&width,&height);
  if(width <= 0 || height <= 0) return;
  auto const area{viewport(width,height)};
  glViewport(0,0,width,height);
  glClearColor(0,0,0,1);
  glClear(GL_COLOR_BUFFER_BIT);
  glViewport(area.position.x,area.position.y,area.size.x,area.size.y);
  glBindTexture(GL_TEXTURE_2D,texture);
  glTexSubImage2D(GL_TEXTURE_2D,0,0,0,render::screen_width,render::screen_height,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
  glBegin(GL_TRIANGLE_STRIP);
  glTexCoord2f(0,0); glVertex2f(-1,1);
  glTexCoord2f(0,1); glVertex2f(-1,-1);
  glTexCoord2f(1,0); glVertex2f(1,1);
  glTexCoord2f(1,1); glVertex2f(1,-1);
  glEnd();
  glfwSwapBuffers(handle.get());
}

} // namespace tfx::platform
