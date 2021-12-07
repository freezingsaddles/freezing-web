from __future__ import absolute_import
import sys
import logging
import inspect


class EagerFormattingAdapter(logging.LoggerAdapter):
    """
    A `logging.LoggerAdapter` that add unterpolation support but performs the
    evaluation immediately if the appropriate loglevel is set.
    """

    def __init__(self, logger, extra=None):
        """
        Initialize the adapter with a logger and a dict-like object which
        provides contextual information. This constructor signature allows
        easy stacking of LoggerAdapters, if so desired.

        You can effectively pass keyword arguments as shown in the
        following example:

        adapter = LoggerAdapter(someLogger, dict(p1=v1, p2="v2"))
        """
        super(EagerFormattingAdapter, self).__init__(logger, extra)

    def _eagerFormat(self, msg, level, args):
        """
        Eagerly apply log formatting if the appropriate level is enabled.

        Otherwise we just drop the log message (and return a string indicating
        that it was suppreseed).
        """
        if self.isEnabledFor(level):
            # Do the string formatting immediately.
            if args:
                return self._getUnterpolatedMessage(msg, args)
            else:
                return msg
        else:
            # Otherwise, just drop the message completely to avoid anything going
            # wrong in the future.  This text shoudl clue one in to what's going
            # on in the bizarre edge case where this ever does show up.
            return "(log message suppressed due to insufficient log level)"

    def _getUnterpolatedMessage(self, msg, args):
        """
        Returns the formatted string, will first attempt str.format and will
        fallback to msg % args as it was originally.

        This is lifted almost wholesale from logging_unterpolation.
        """
        original_msg = msg
        if isinstance(args, dict):
            # special case handing for unpatched logging supporting
            # statements like:
            # logging.debug("a %(a)d b %(b)s", {'a':1, 'b':2})
            args = (args,)

        try:
            msg = msg.format(*args)
        except UnicodeEncodeError:
            # This is most likely due to formatting a non-ascii string argument
            # into a bytestring, which the %-operator automatically handles
            # by casting the left side (the "msg" variable) in this context
            # to unicode. So we'll do that here

            if sys.version_info >= (
                3,
                0,
            ):
                # this is most likely unnecessary on python 3, but it's here
                # for completeness, in the case of someone manually creating
                # a bytestring
                unicode_type = str
            else:
                unicode_type = unicode

            # handle the attempt to print utf-8 encoded data, similar to
            # %-interpolation's handling of unicode formatting non-ascii
            # strings
            msg = unicode_type(msg).format(*args)

        except ValueError:
            # From PEP-3101, value errors are of the type raised by the format
            # method itself, so see if we should fall back to original
            # formatting since there was an issue
            if "%" in msg:
                msg = msg % args
            else:
                # we should NOT fall back, since there's no possible string
                # interpolation happening and we want a meaningful error
                # message
                raise

        if msg == original_msg and "%" in msg:
            # there must have been no string formatting methods
            # used, given the presence of args without a change in the msg
            # fall back to original formatting, including the special case
            # for one passed dictionary argument
            msg = msg % args

        return msg

    def debug(self, msg, *args, **kwargs):
        """
        Delegate a debug call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Delegate an info call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Delegate a warning call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        """
        Delegate a warning call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """
        Delegate an error call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """
        Delegate an exception call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        kwargs["exc_info"] = 1
        self.log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Delegate a critical call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        self.log(logging.CRITICAL, msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        """
        Delegate a log call to the underlying logger, after adding
        contextual information from this adapter instance.
        """
        msg, kwargs = self.process(msg, kwargs)
        # We explicitly do not pass the args into the log method here, since
        # they should be "used up" by the eagerFormat method.
        self.logger.log(level, self._eagerFormat(msg, level, args), **kwargs)

    def isEnabledFor(self, level):
        """
        See if the underlying logger is enabled for the specified level.
        """
        return self.logger.isEnabledFor(level)


class AutoLogger(object):
    """
    A logger proxy object, with all of the methods and attributes of C{Logger}.

    When an attribute (e.g., "debug") is requested, inspects the stack for the
    calling module's name, and passes that name to C{logging.getLogger}.

    What this means is that you can instantiate an C{AutoLogger} anywhere, and
    when you call it, the log entry shows the module where you called it, not
    where it was created.

    C{AutoLogger} also inspects the local variables where it is called, looking
    for C{self}. If C{self} exists, its classname is added to the module name.
    """

    def __init__(self, adapter_class=None, adapter_args=None, adapter_kwargs=None):
        if adapter_args is None:
            adapter_args = []
        if adapter_kwargs is None:
            adapter_kwargs = {}

        self.adapter_class = adapter_class
        self.adapter_args = adapter_args
        self.adapter_kwargs = adapter_kwargs

    def __getattr__(self, name):
        if "self" in inspect.currentframe().f_locals:
            other = inspect.currentframe().f_locals["self"]
            caller_name = "%s.%s" % (
                other.__class__.__module__,
                other.__class__.__name__,
            )
        else:
            caller_name = inspect.currentframe(1).f_globals["__name__"]
        logger = logging.getLogger(caller_name)

        if self.adapter_class:
            logger = self.adapter_class(
                logger, *self.adapter_args, **self.adapter_kwargs
            )

        return getattr(logger, name)


log = AutoLogger(EagerFormattingAdapter)


def log_exceptions(fn):
    """A decorator designed to wrap a function and log any exception that method produces.

    The exception will still be raised after being logged.

    Also logs (at the trace level) the arguments to every call.

    Currently this is only designed for module-level functions.  Not sure what happens if a method is decorated
    with this (since logger is resolved from module name).
    """

    def wrapper(*args, **kwargs):
        try:
            a = args or []
            a = [str(x)[:255] for x in a]
            kw = kwargs or {}
            kw = dict([(str(k)[:255], str(v)[:255]) for k, v in kw.items()])
            log.debug("Calling %s.%s %r %r" % (fn.__module__, fn.__name__, a, kw))
            return fn(*args, **kwargs)
        except Exception as e:
            log.error("Error calling function %s: %s" % (fn.__name__, e))
            log.exception(e)
            raise

    wrapper.__name__ = fn.__name__
    return wrapper
