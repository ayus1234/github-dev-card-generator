FROM nginx:alpine

# Copy the frontend HTML file
COPY index.html /usr/share/nginx/html/index.html.template

# Create an entrypoint script to replace BACKEND_URL at runtime
RUN echo '#!/bin/sh' > /docker-entrypoint.d/90-envsubst-backend.sh && \
    echo 'export BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"' >> /docker-entrypoint.d/90-envsubst-backend.sh && \
    echo 'sed "s|http://localhost:8080|${BACKEND_URL}|g" /usr/share/nginx/html/index.html.template > /usr/share/nginx/html/index.html' >> /docker-entrypoint.d/90-envsubst-backend.sh && \
    chmod +x /docker-entrypoint.d/90-envsubst-backend.sh

# Expose the frontend port
EXPOSE 80
