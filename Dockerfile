## Stage 1: Build environment
FROM alpine AS environment

# Configure environment
ENV NO_AT_BRIDGE=1 GTK_THEME=Adwaita:dark

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

# Set a directory for the app
WORKDIR /opt/flow-dashboard

# Copy necessary files to container
COPY src/ src/

# Start the app
ENTRYPOINT ["python3", "src/main.py"]
