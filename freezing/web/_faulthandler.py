import faulthandler
import signal

# Register this super early so we can get a stack trace if
# there is a problem in initializing the config module
faulthandler.register(signal.SIGUSR1)
