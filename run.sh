docker run --runtime=runsc --rm -it \
  -v "$(pwd)/server.py:/server.py" \
  -p 8000:8000 \
  python:3.9.21-alpine3.21 \
  python /server.py
