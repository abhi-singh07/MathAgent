import os
from pesudo_main import pseudo_main
from flaml import oai
import json
from dotenv import load_dotenv


def main():
    pseudo_main(config_list)

if __name__ == "__main__":
    load_dotenv()
    config_list = None
    oai.retry_timeout = 3600
    main()
