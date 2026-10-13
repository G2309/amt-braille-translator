# Sitio estático de la presentación servido con Caddy, liviano para que el costo en Railway sea mínimo
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY index.html styles.css app.js /srv/
COPY assets /srv/assets
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
