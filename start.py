import subprocess
import shlex

HTTP_COMMAND = "sudo http-server /home/pi/dht/public -p 80"
DHT_COMMAND = "nohup python3 /home/pi/dht/dht2.py"


print("starting http server")
subprocess.run(shlex.shlex(HTTP_COMMAND))
print("done")

print("starting the dht server")
subprocess.run(shlex.shlex(DHT_COMMAND))
print("done")

