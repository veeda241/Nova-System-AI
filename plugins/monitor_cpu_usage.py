"""
Plugin: monitor cpu usage
Description: Create a plugin to monitor CPU usage
Author: Nova Auto-Generated
"""

def run(params: dict = None) -> str:
    """Main entry point for the plugin.

    Parameters:
        params (dict): Optional dictionary of parameters. Currently, no parameters are supported.
    
    Returns:
        str: A user-friendly string result indicating the current CPU usage percentage.
    """
    try:
        import psutil
        cpu_usage = psutil.cpu_percent()
        return f"Current CPU usage: {cpu_usage}%"
    except Exception as e:
        return f"Error: Unable to retrieve CPU usage. {str(e)}"


def main(params: dict = None) -> str:
    """Call the run function with optional parameters."""
    return run(params)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        params = {}
        for arg in sys.argv[1:]:
            key, value = arg.split("=")
            params[key] = value
        result = main(params)
    else:
        result = main()
    print(result)