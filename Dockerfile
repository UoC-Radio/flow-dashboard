## Stage 1: Build environment
FROM alpine AS environment

# Install dependencies
RUN apk add python3 \
	py3-gobject3 \
	py3-lxml \
	gtk+3.0 \
	libcanberra-gtk3 \
	ttf-cantarell \
	adwaita-icon-theme \
	font-noto


## Stage 2: Run app
FROM environment AS app

# Port where the broadway daemon listens on
EXPOSE 8085/tcp

# Configure environment
ENV NO_AT_BRIDGE=1 GTK_THEME=Adwaita:dark GDK_BACKEND=broadway BROADWAY_DISPLAY=:5

# Set a directory for the app
WORKDIR /opt/flow-dashboard

# Copy necessary files to container
COPY init.sh src/ src/

# Start the app
ENTRYPOINT ["/bin/sh", "./src/init.sh"]
