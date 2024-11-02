import yaml
#Separate config.py to we can import it to be used as global config, without having it to be passed to every function/class
with open("../etc/general.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.Loader)