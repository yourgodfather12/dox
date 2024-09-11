import json
import asyncio
import aiohttp
import logging
from aiohttp import ClientSession
import signal
from contextlib import asynccontextmanager
from tqdm.asyncio import tqdm
import aiofiles

# Load config from file
with open('config.json', 'r') as f:
    config = json.load(f)

# Logging configuration
logging.basicConfig(
    filename=config.get('log_file', None),  # Log to file if specified in config
    level=logging.getLevelName(config.get('log_level', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

# API configuration
NUMVERIFY_API_KEY = config.get('NUMVERIFY_API_KEY', 'your_api_key_here')
DEFAULT_TIMEOUT = config.get('DEFAULT_TIMEOUT', 5)
RETRY_COUNT = config.get('RETRY_COUNT', 3)
RETRY_DELAY = config.get('RETRY_DELAY', 2)
OUTPUT_FILE = config.get('output_file', 'validation_results.txt')

# Cache for phone validation results
class AsyncCache:
    def __init__(self, maxsize=100):
        self.cache = {}
        self.maxsize = maxsize
        self.lock = asyncio.Lock()

    async def get(self, key):
        async with self.lock:
            return self.cache.get(key)

    async def set(self, key, value):
        async with self.lock:
            if len(self.cache) >= self.maxsize:
                self.cache.pop(next(iter(self.cache)))  # FIFO eviction
            self.cache[key] = value

    async def close(self):
        async with self.lock:
            self.cache.clear()

cache = AsyncCache(maxsize=100)

@asynccontextmanager
async def aiohttp_session():
    """Manage the lifecycle of an aiohttp ClientSession."""
    async with ClientSession(connector=aiohttp.TCPConnector(limit=100)) as session:
        yield session

async def validate_phone(phone, session):
    """Validate phone using Numverify API with retry logic."""
    # Check if result is cached
    cached_result = await cache.get(phone)
    if cached_result is not None:
        logger.info(f"Cache hit for phone: {phone}")
        return cached_result

    url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_API_KEY}&number={phone}"
    try:
        async with session.get(url, timeout=DEFAULT_TIMEOUT) as response:
            if response.status == 200:
                data = await response.json()
                if 'valid' in data and 'location' in data:
                    result = data['valid'], data['location']
                    await cache.set(phone, result)  # Cache the result
                    return result
            logger.error(f"Invalid response from Numverify: {response.status}")
            return False, None
    except aiohttp.ClientError as e:
        logger.error(f"ClientError for phone {phone}: {e}")
        return False, None

async def retry_request(func, *args, **kwargs):
    """Retry function with exponential backoff."""
    for attempt in range(RETRY_COUNT):
        try:
            return await func(*args, **kwargs)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Attempt {attempt + 1}/{RETRY_COUNT} failed: {e}")
            if attempt < RETRY_COUNT - 1:
                await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                logger.error(f"Max retries reached. Exception: {e}")
                return False, None

async def batch_validate_phones(phone_list):
    """Batch validate phones with retry and async file output."""
    async with aiohttp_session() as session:
        tasks = [retry_request(validate_phone, phone, session) for phone in phone_list]
        results = []

        async for task in tqdm(asyncio.as_completed(tasks), total=len(phone_list)):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                results.append((False, None))  # Log failure as a tuple (False, None)
                logger.error(f"Error validating phone: {e}")

        async with aiofiles.open(OUTPUT_FILE, 'w') as file:
            for phone, result in zip(phone_list, results):
                await file.write(f"Phone: {phone}, Result: {result}\n")

        return results

def handle_exit(loop):
    """Gracefully handle exit signal."""
    logger.info("Shutting down gracefully...")
    tasks = asyncio.all_tasks(loop)
    for task in tasks:
        task.cancel()

def main():
    loop = asyncio.get_event_loop()
    phones = ['1234567890', '0987654321', '5555555555']

    # Signal handling for graceful shutdown
    for signame in {'SIGINT', 'SIGTERM'}:
        loop.add_signal_handler(
            getattr(signal, signame), lambda: handle_exit(loop)
        )

    try:
        loop.run_until_complete(batch_validate_phones(phones))
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
