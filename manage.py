#!/usr/bin/env python


def main():
    from biblioteci import create_app, create_manager
    app = create_app()
    manager = create_manager(app)
    manager.run()


if __name__ == '__main__':
    main()
