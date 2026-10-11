# Sitio estático de la presentación servido con Caddy, liviano para que el costo en Railway sea mínimo
FROM caddy:2-alpine
COPY index.html styles.css app.js /srv/
COPY assets /srv/assets
CMD ["sh", "-c", "caddy file-server --root /srv --listen :${PORT:-8080}"]
