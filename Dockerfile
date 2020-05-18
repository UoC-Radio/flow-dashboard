# Start from this image
FROM debian

# Set a directory for the app
WORKDIR /opt/flow-dashboard

# Copy necessary files to container
COPY src/* ./
COPY gallery/logo.png ./gallery/logo.png

# Configure environment
ENV DEBIAN_FRONTEND=noninteractive SSL_CERT_DIR=/etc/ssl/certs GTK_THEME=Adwaita:dark

# Install dependencies
RUN apt update && \
        apt install -y apt-utils && \
        apt upgrade -y && \
        apt install -y gir1.2-gtk-3.0 python3-gi python3-gi-cairo python3-lxml && \
        apt install -y dbus-x11 && \
        apt install -y ca-certificates && \
        update-ca-certificates --fresh

# Run the command
CMD ["python3", "./main.py"]
