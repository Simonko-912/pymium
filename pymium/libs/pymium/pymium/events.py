"""Event and EventTarget primitives shared by every live object."""


class Event:
    def __init__(self, type_, target=None, props=None):
        self.type = type_
        self.target = target
        self._default_prevented = False
        self._stopped = False
        self._props = dict(props or {})
        self._hits = 0

    def __getattr__(self, name):
        props = self.__dict__.get("_props")
        if props is not None and name in props:
            return props[name]
        raise AttributeError(name)

    def prevent_default(self):
        self._default_prevented = True

    def preventDefault(self):
        self.prevent_default()

    def stop_propagation(self):
        self._stopped = True

    def stopPropagation(self):
        self.stop_propagation()

    @property
    def default_prevented(self):
        return self._default_prevented


class EventTarget:
    def __init__(self, owner=None):
        object.__setattr__(self, "_listeners", {})
        object.__setattr__(self, "_owner", owner)

    def add_event_listener(self, name, callback, once=False):
        self._listeners.setdefault(name, []).append((callback, once))

    def addEventListener(self, name, callback, once=False):
        self.add_event_listener(name, callback, once)

    def remove_event_listener(self, name, callback):
        bucket = self._listeners.get(name)
        if bucket:
            self._listeners[name] = [
                pair for pair in bucket if pair[0] is not callback
            ]

    def removeEventListener(self, name, callback):
        self.remove_event_listener(name, callback)

    def dispatch_event(self, event):
        event.target = self._owner if self._owner is not None else event.target
        for callback, once in list(self._listeners.get(event.type, ())):
            result = callback(event)
            if once:
                self.remove_event_listener(event.type, callback)
            return result
        return None

    def dispatchEvent(self, event):
        return self.dispatch_event(event)

    def on(self, name):
        def register(callback):
            self.add_event_listener(name, callback)
            return callback

        return register

    def has_listeners(self, name):
        return bool(self._listeners.get(name))