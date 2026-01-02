Deployment and scaling guide
===========================

This project supports three deployment modes:

- Local development: `docker-compose`
- Docker Swarm: `docker stack deploy`
- Kubernetes: `kubectl apply -f k8s/`

Prerequisites
-------------

- Docker (Desktop) and Docker Compose
- For Swarm: Docker Engine (init swarm with `docker swarm init`)
- For Kubernetes: `kubectl` connected to a cluster and images available in a registry the cluster can pull from.

Build the image
---------------

The Swarm and Kubernetes manifests use an image named `dbteamv2:alfa`.

Locally you can build it and tag it:

```bash
docker build -t dbteamv2:alfa .
```

Build the nginx image that bakes static files into the image:

```bash
docker build -t dbteamv2-nginx:alfa -f deploy/Dockerfile.nginx .
```

Or use the helper script:

```bash
./scripts/build_images.sh
```

If you deploy to a remote Swarm/Kubernetes cluster, tag and push to your registry:

```bash
docker tag dbteamv2:alfa myregistry.example.com/me/dbteamv2:alfa
docker push myregistry.example.com/me/dbteamv2:alfa
```

Docker Compose (development)
----------------------------

Build and run with Compose (already added in `docker-compose.yml`):

```bash
docker-compose up --build -d
```

This runs `nginx`, `ai_server` and `stream_server`. Nginx serves the `web/` folder and proxies `/ai/` and `/stream/`.

Docker Swarm
-----------

1. Ensure Swarm mode is initialized:

```bash
docker swarm init
```

2. Build the image and make it available to Swarm managers (either push to a registry or build on the nodes):

```bash
docker build -t dbteamv2:alfa .
# push if necessary
```

3. Deploy the stack:

```bash
docker stack deploy -c docker-stack.yml dbteamv2
```

4. Scale services:

```bash
docker service scale dbteamv2_stream_server=3
```

Notes:
- The `docker-stack.yml` uses bind mounts to `./web` and `./deploy/nginx.conf`. When deploying on remote machines, ensure those paths exist, or modify the stack to use a shared volume or a custom nginx image that contains the static files.

For this repository we've added a custom nginx image approach. If you use the `docker-stack.yml` provided, build and push `dbteamv2-nginx:alfa` first and ensure the swarm can pull it:

```bash
docker build -t dbteamv2-nginx:alfa -f deploy/Dockerfile.nginx .
docker tag dbteamv2-nginx:alfa myregistry.example.com/me/dbteamv2-nginx:alfa
docker push myregistry.example.com/me/dbteamv2-nginx:alfa
```

Kubernetes
----------

1. Build and push the image to a registry accessible by your cluster (see above).
2. Apply manifests:

```bash
kubectl apply -f k8s/deployments.yaml
```

Before applying to Kubernetes, build and push the nginx image as the manifests expect `dbteamv2-nginx:alfa`:

```bash
docker build -t dbteamv2-nginx:alfa -f deploy/Dockerfile.nginx .
docker tag dbteamv2-nginx:alfa myregistry.example.com/me/dbteamv2-nginx:alfa
docker push myregistry.example.com/me/dbteamv2-nginx:alfa
```

Also ensure `dbteamv2:alfa` is pushed to the same registry and update image references in `k8s/deployments.yaml` if you use a custom registry.

3. Expose the nginx-proxy service via a LoadBalancer or configure an Ingress.

Notes & next steps
------------------
- The `stream_server` will attempt to run `ffmpeg` inside the container if `live_settings` contain a `target` URL. The base `Dockerfile` includes `ffmpeg` so streaming should work inside containers.
- For production-grade deployment consider:
  - Building a custom `nginx` image that bakes the `web/` static files into the image (avoids host path mounts).
  - Using a registry and CI pipeline to build & publish images.
  - Using Kubernetes Ingress + cert-manager for TLS.

If you want, I can:
- Add a `Dockerfile.nginx` that bakes `web/` into a custom `nginx` image and update manifests to use it.
- Produce a `kustomization.yaml` and Helm chart for more flexible k8s deployments.

Local DNS for torrent URLs
-------------------------

To support friendly torrent URLs like `abcd1234.torrents.local/torrents/file.torrent` you can run a tiny local DNS server provided in `tools/local_dns.py`.

Requirements:
- `pip install dnslib`
- Run the script with elevated privileges to bind port 53 (or adapt to a non-privileged port and a DNS forwarder):

```bash
python tools/local_dns.py --domain torrents.local --address 127.0.0.1
```

Then set your system DNS server to `127.0.0.1` (or the address of the machine running the DNS server). On Windows use the network adapter DNS settings.

The `stream_server` exposes `/stream/torrent_url` to generate the URL for a torrent and `/torrents/<name>` to serve torrent files from `data/torrents`.

Example:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name":"myfile.torrent"}' http://127.0.0.1:8082/stream/torrent_url
```

Response:

```json
{ "ok": true, "url": "http://myfile.torrent.torrents.local/torrents/myfile.torrent" }
```

Note: wildcard DNS requires a DNS server; the hosts file does not support wildcards.

Dockerized local DNS (recommended for Docker Desktop)
-----------------------------------------------

If you prefer not to run a host DNS service, you can run a lightweight `dnsmasq` container that provides wildcard DNS for development. `docker-compose.yml` already includes a `local_dns` service.

Start it with Compose:

```bash
docker-compose up -d local_dns
```

On Docker Desktop for Windows, enable the DNS server by configuring your system DNS to point to the Docker host IP (often `127.0.0.1` for WSL2 or the Docker for Windows host). For many setups simply running the container makes the DNS available to containers; to use it from the host, adjust your adapter DNS settings to `127.0.0.1`.

Windows helper
--------------

Run `scripts/run_local_dns.ps1` as Administrator to start `tools/local_dns.py` in background on Windows.

