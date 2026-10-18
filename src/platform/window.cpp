#include "window.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>
#ifdef _WIN32
#include <GL/glext.h>
#endif // _WIN32

namespace tfx::platform {
namespace {
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

window::window(unsigned int const scale) : handle{nullptr, glfwDestroyWindow} {
  /// Match Darker's floating-window sizing and nearest-neighbour presentation; only the final CPU image uses OpenGL
  bool const automatic{scale == 0}, compositor_sizing{automatic && glfwGetPlatform() == GLFW_PLATFORM_WAYLAND};
  glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,2);
  glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,1);
  glfwWindowHint(GLFW_VISIBLE,GLFW_FALSE);
  glfwWindowHint(GLFW_MAXIMIZED,compositor_sizing ? GLFW_TRUE : GLFW_FALSE);
  auto const initial_scale{static_cast<int>(scale ? scale : 2)};
  handle.reset(glfwCreateWindow(render::display_width * initial_scale,render::display_height * initial_scale,"TFX C++ — scene inspection",nullptr,nullptr));
  if(!handle) throw std::runtime_error{"cannot create the TFX window"};
  if(automatic && !compositor_sizing) {
    if(auto *monitor{glfwGetPrimaryMonitor()}) {
      int x{0}, y{0}, width{0}, height{0}, left{0}, top{0}, right{0}, bottom{0};
      glfwGetMonitorWorkarea(monitor,&x,&y,&width,&height);
      glfwGetWindowFrameSize(handle.get(),&left,&top,&right,&bottom);
      int const fit{std::max(1,std::min((width - left - right) / render::display_width,(height - top - bottom) / render::display_height))};
      glfwSetWindowSize(handle.get(),render::display_width * fit,render::display_height * fit);
      glfwSetWindowPos(handle.get(),x + left + (width - left - right - render::display_width * fit) / 2,y + top + (height - top - bottom - render::display_height * fit) / 2);
    }
  }
  glfwShowWindow(handle.get());
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
  glfwSetWindowFocusCallback(handle.get(),[](GLFWwindow *const target, int const focused){
    if(!focused) glfwSetInputMode(target,GLFW_CURSOR,GLFW_CURSOR_NORMAL);
  });
}

window::~window() {
  glDeleteTextures(1,&texture);
}
GLFWwindow *window::get() const {
  return handle.get();
}
bool window::focused() const {
  return glfwGetWindowAttrib(handle.get(),GLFW_FOCUSED) == GLFW_TRUE;
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
