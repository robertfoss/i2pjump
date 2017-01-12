# i2pjump - Run an I2P Jump Server
# License - This is free and unencumbered software released into the public domain.
# Running - See README.md
FROM python:3-alpine
WORKDIR /i2pjump
COPY i2pjump.py .
CMD python i2pjump.py --host 0.0.0.0
