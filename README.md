# i2pjump

I2P jump service. A sort of slave DNS server for I2P.

## Running

### Python

`$ python i2pjump.py`

### Docker

`$ docker run --net="host" -p 8081:8081 -v $(pwd)/hosts.db:/i2pjump/hosts.db:rw geti2p/i2pjump:latest`

