# Sandboxed execution environment for LangGraph agent
FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set up locales
RUN apt-get update && apt-get install -y locales && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Install basic utilities first
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    ca-certificates \
    gnupg \
    lsb-release \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Ripgrep
RUN wget https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep_14.1.0-1_amd64.deb \
    && dpkg -i ripgrep_14.1.0-1_amd64.deb \
    && rm ripgrep_14.1.0-1_amd64.deb

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install global Python packages
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Create non-root user for security
RUN useradd -m -s /bin/bash -u 1000 user && \
    echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up workspace
WORKDIR /home/user

# Create standard directories
RUN mkdir -p /home/user/workspace && \
    mkdir -p /mnt/user-data && \
    mkdir -p /mnt/skills && \
    mkdir -p /mnt/transcripts && \
    chown -R user:user /home/user

# Set read-only permissions for mounted directories
RUN chmod 755 /mnt/user-data /mnt/skills /mnt/transcripts

# Switch to non-root user
USER user

# Set up Python virtual environment
RUN python3 -m venv /home/user/.venv
ENV PATH="/home/user/.venv/bin:$PATH"

# Install commonly used packages in the sandbox
RUN pip install --no-cache-dir \
    requests \
    numpy \
    pandas \
    matplotlib \
    pytest \
    black \
    ruff \
    ipython

# Set working directory to workspace
WORKDIR /home/user/workspace

# Copy entrypoint script
COPY --chown=user:user docker/entrypoint.sh /home/user/entrypoint.sh
RUN chmod +x /home/user/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "print('healthy')" || exit 1

# Set default command
ENTRYPOINT ["/home/user/entrypoint.sh"]
CMD ["/bin/bash"]
