Guía rápida para claves GPG

- Generar una nueva clave (interactiva):
  gpg --full-generate-key

- Exportar la clave pública para distribuirla con el instalador o publicarla en Releases:
  gpg --armor --export youremail@example.com > public.key

- Coloca `public.key` en `keys/public.key` en la raíz del repositorio o publica la clave en un URL
  público y establece la variable `GPG_PUBKEY_URL` antes de ejecutar `install.sh`.

- Firmar `checksums.txt` con la clave:
  ./scripts/sign_checksums.sh yourkeyid
