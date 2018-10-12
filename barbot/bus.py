
import logging
from event_bus import EventBus


_logger = logging.getLogger('Bus')


class BarbotEventBus(EventBus):
    
    def emit(self, event: str, *args, **kwargs) -> None:
        _logger.debug('event: {} ({})'.format(event, len(self._events[event])))
        return super().emit(event, *args, **kwargs)
        
bus = BarbotEventBus()

