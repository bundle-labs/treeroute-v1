"""``py -3.9 -m treeroute``: the only entry point. The launcher pins every pool before numpy loads."""

from treeroute import launch

if __name__ == "__main__":
    launch.main()
