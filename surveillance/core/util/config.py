import yaml
#Separate config.py to we can import it to be used as global config, without having it to be passed to every function/class
with open("conf/general.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)