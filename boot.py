import micropython, hub
micropython.alloc_emergency_exception_buf(128)
hub.config["hub_os_enable"] = True