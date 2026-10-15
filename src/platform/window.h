#pragma once

#include <memory>
#include <string>
#include <GLFW/glfw3.h>
#include "render/framebuffer.h"

namespace tfx::platform {

class glfw_runtime {
public:
  glfw_runtime();
  ~glfw_runtime();
  glfw_runtime(glfw_runtime const&) = delete;
  glfw_runtime &operator=(glfw_runtime const&) = delete;
};

class window {
private:
  glfw_runtime runtime;
  std::unique_ptr<GLFWwindow, decltype(&glfwDestroyWindow)> handle;
  unsigned int texture{0};

public:
  window(unsigned int scale);
  ~window();
  window(window const&) = delete;
  window &operator=(window const&) = delete;
  GLFWwindow *get() const;
  bool focused() const;
  bool poll();
  void title(std::string const &text);
  void present(std::span<render::rgba_pixel const> pixels);
};

} // namespace tfx::platform
