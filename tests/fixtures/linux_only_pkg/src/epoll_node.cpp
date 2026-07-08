// 의도적으로 linux 전용 헤더 사용 — 맥 빌드 실패 = 이 픽스처의 존재 이유 (P4.4)
#include <sys/epoll.h>

#include <cstdio>

int main() {
  int fd = epoll_create1(0);
  std::printf("epoll fd=%d\n", fd);
  return fd >= 0 ? 0 : 1;
}
