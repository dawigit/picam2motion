# picam2motion

### Picamera2 based simple motion detection

tested with debian bookworm / raspberry pi zero

### install

`./install_picam2motion.sh`

or

`sudo apt install -y python3-picamera2 python3-opencv python3-numpy`


### usage

`picam2motion.py [-h] [-s SAVE] [-H HOST] [-p PORT] [-z ZOOM] [-d DIFF]`

- SAVE save path of motion files
- HOST syslog host
- PORT syslog port
- ZOOM zoom to image center
- DIFF threshold for pixel difference

