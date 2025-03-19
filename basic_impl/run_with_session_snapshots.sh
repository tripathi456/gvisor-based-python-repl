# docker run --runtime=runsc --rm -it \
#   -v "$(pwd)/forevervm_minimal:/app" \
#   -v "$(pwd)/snapshots:/var/forevervm/snapshots" \
#   -p 8000:8000 \
#   python:3.9.21-alpine3.21 \
#   sh -c "cd /app && python main.py"

docker run --runtime=runsc --rm -it \
  -v "$(pwd)/forevervm_minimal:/app/forevervm_minimal" \
  -v "$(pwd)/snapshots:/var/forevervm/snapshots" \
  -p 8000:8000 \
  python:3.9.21-alpine3.21 \
  sh -c "cd /app/forevervm_minimal && pip install flask && python main.py"