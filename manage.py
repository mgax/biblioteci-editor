#!/usr/bin/env python

from biblioteci import create_app, create_manager


def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    app = create_app()
    manager = create_manager(app)
    manager.run()


if __name__ == '__main__':
    main()
