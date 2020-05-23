## Stage 1: Build environment
FROM debian AS environment

# Configure environment
ENV DEBIAN_FRONTEND=noninteractive SSL_CERT_DIR=/etc/ssl/certs GTK_THEME=Adwaita:dark

# Install dependencies
RUN apt update && \
        apt install -y apt-utils && \
        apt install -y \
		gir1.2-gtk-3.0 \
		python3-gi \
		python3-gi-cairo \
		python3-lxml \
		dbus-x11 \
		ca-certificates && \
        update-ca-certificates --fresh && \
	rm -rf /var/lib/apt/lists/*


## Stage 2: Run app
FROM environment AS app

# Set a directory for the app
WORKDIR /opt/flow-dashboard

# Copy necessary files to container
COPY src/ src/

# Start the app
ENTRYPOINT ["python3", "src/main.py"]
