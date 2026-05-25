FROM iregistry.baidu-int.com/repo_zero/c2rust-arena:latest

RUN rm -f /etc/apt/apt.conf /etc/apt/apt.conf.d/*proxy*

# 删除私有源并清理 apt 缓存
RUN rm -f /etc/apt/sources.list.d/baidu*.list /etc/apt/sources.list.d/nvidia*.list \
    && rm -rf /var/lib/apt/lists/*
# 安装 Rust
RUN apt  update
RUN apt install -y rustc

# 复制宿主机的 libstdc++.so.6.0.30（需要 GLIBCXX_3.4.29 支持）
COPY libstdc++.so.6.0.30 /opt/compiler/gcc-12/lib/

# 创建多个编译器版本的库路径
RUN mkdir -p /lib64 /opt/compiler/gcc-12/lib /opt/compiler/gcc-12/lib64 \
    /opt/compiler/gcc-8.2/lib /opt/compiler/gcc-8.2/lib64

# 链接动态链接器 - 支持标准路径和多个编译器路径
RUN ln -sf /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /lib64/ld-linux-x86-64.so.2 && \
    ln -sf /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /opt/compiler/gcc-12/lib64/ld-linux-x86-64.so.2 && \
    ln -sf /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /opt/compiler/gcc-8.2/lib64/ld-linux-x86-64.so.2

# 链接共享库到 gcc-12 路径
RUN cd /opt/compiler/gcc-12/lib && \
    rm -f libstdc++.so.6 && \
    ln -sf libstdc++.so.6.0.30 libstdc++.so.6 && \
    ln -sf /usr/lib/x86_64-linux-gnu/libm.so.6 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libgcc_s.so.1 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libc.so.6 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libpthread.so.0 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libdl.so.2 . 2>/dev/null || true

# 链接共享库到 gcc-8.2 路径（使用容器自带的 libstdc++）
RUN cd /opt/compiler/gcc-8.2/lib && \
    ln -sf /usr/lib/x86_64-linux-gnu/libstdc++.so.6 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libm.so.6 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libgcc_s.so.1 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libc.so.6 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libpthread.so.0 . 2>/dev/null || true && \
    ln -sf /usr/lib/x86_64-linux-gnu/libdl.so.2 . 2>/dev/null || true

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]