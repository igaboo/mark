import re, random, asyncio, logging, traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Callable, List
from listing import Listing
import discord
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException

handler = RotatingFileHandler('error_log.txt', maxBytes=5 * 1024 * 1024, backupCount=3)
handler.setLevel(logging.ERROR)
log_format = '%(asctime)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.basicConfig(
    level=logging.ERROR,
    format=log_format
)

LOADING_MESSAGES = [
    "Checking the oil...",
    "Haggling with the seller...",
    "Checking the carfax...",
    "Test driving the car...",
    "Negotiating the price...",
    "Taking out a loan...",
    "Thinking about buying it...",
    "Checking the tires...",
    "Looking for scratches...",
    "Imagining driving it...",
]
TIMEOUT = 10
RETRY = 5

def init_webdriver() -> webdriver.Firefox:
    """
    Initialize a headless Firefox webdriver.
    """
    options = Options()
    options.add_argument('--headless')
    return webdriver.Firefox(service=Service('/usr/local/bin/geckodriver'), options=options)

def logError(message: str) -> None:
    logging.error(f"============= {datetime.now()} =============== BEGIN")
    logging.error(message)
    logging.error(traceback.format_exc())
    logging.error("=========================== END")

def get_element(
    driver: WebDriver, 
    name: str, 
    by: By, 
    selector: str, 
    callback: Callable[[WebElement], str] = lambda x : x, 
    wait = False
) -> Optional[str]:
    """
    Get an element and apply a callback function to it.
    """
    try:
        if wait:
            element = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((by, selector))
            )
        else:
            element = driver.find_element(by, selector)
        return callback(element)
    except NoSuchElementException as e:
        print(f"Error getting {name}: NoSuchElementException")
        return None
    except Exception as e:
        print(f"Error getting {name}: {e}")
        return None

def get_elements(
    driver: WebDriver, 
    name: str, 
    by: By, 
    selector: str, 
    callback: Callable[[List[WebElement]], str] = lambda x : x, 
    wait = False
) -> Optional[str]:
    """
    Get a list of elements and apply a callback function to them.
    """
    try:
        if wait:
            elements = WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_all_elements_located((by, selector))
            )
        else:
            elements = driver.find_elements(by, selector)
        return callback(elements)
    except NoSuchElementException as e:
        print(f"Error getting {name}: NoSuchElementException")
        return None
    except Exception as e:
        print(f"Error getting {name}")
        return None

def get_any(
    *args: Optional[str], 
    validate: Callable[[Optional[str]], bool] = lambda x : True
) -> Optional[str]:
    """
    Get the first non-None element from a list.
    """
    for arg in args:
        if arg is not None and validate(arg):
            return arg
        elif arg is not None:
            print(f"Value '{arg}' did not pass validation.")
    return None

async def send_message_with_retry(
    message: discord.Message, 
    embed: discord.Embed, 
    retries: int = RETRY
) -> Optional[discord.Message]:
    """
    Send a message with a retry mechanism
    """
    try:
        return await message.channel.send(embed=embed)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = e.response.headers.get('Retry-After', 5)
            print(f"Rate limited while trying to send, retrying in {retry_after} seconds ({RETRY - retries}/{RETRY})...")
            await asyncio.sleep(float(retry_after))
            if retries > 0:
                return await send_message_with_retry(message, embed, retries=retries-1)
            else:
                raise Exception("Max retries reached.")

async def edit_message_with_retry(
    message: discord.Message, 
    embed: discord.Embed, 
    retries: int = RETRY
) -> None:
    """
    Edit a message with a retry mechanism
    """
    try:
        await message.edit(embed=embed)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = e.response.headers.get('Retry-After', 5)
            print(f"Rate limited while trying to edit, retrying in {retry_after} seconds ({RETRY - retries}/{RETRY})...")
            await asyncio.sleep(float(retry_after))
            if retries > 0:
                await edit_message_with_retry(message, embed, retries=retries-1)
            else:
                raise Exception("Max retries reached.")

async def delete_message_with_retry(
    message: discord.Message,
    retries: int = RETRY
) -> None:
    """
    Delete a message with a retry mechanism
    """
    try:
        await message.delete()
    except discord.errors.HTTPException as e:
        if e.status == 429:
            retry_after = e.response.headers.get('Retry-After', 5)
            print(f"Rate limited while trying to delete, retrying in {retry_after} seconds ({RETRY - retries}/{RETRY})...")
            await asyncio.sleep(float(retry_after))
            if retries > 0:
                await delete_message_with_retry(message, retries=retries-1)
            else:
                raise Exception("Max retries reached.")

def build_embed(author: discord.User) -> discord.Embed:
    """
    Build a Discord embed.
    """
    embed = discord.Embed(description=random.choice(LOADING_MESSAGES), color=0x1877f2)
    if author: embed.set_author(name=f"Look what {author.name} found!", icon_url=author.avatar)
    return embed

def update_embed(embed: discord.Embed,listing: Listing) -> discord.Embed:
    """
    Update a Discord embed with new scraped results.
    """    
    if listing.title: 
        embed.title = listing.title
    if listing.description: 
        embed.description = listing.description
    if listing.url: 
        embed.url = listing.url
    if listing.price: 
        embed.add_field(
            name='Price', 
            value=listing.price, 
            inline=True
        )
    if listing.mileage: 
        embed.add_field(
            name='Mileage', 
            value=listing.mileage, 
            inline=True
        )
    if listing.transmission: 
        embed.add_field(
            name='Transmission', 
            value=listing.transmission, 
            inline=True
        )
    if listing.image_url: 
        embed.set_image(
            url=listing.image_url
        )
    if listing:
        if listing.posted and listing.location:
            footer = f"Posted {listing.posted} in {listing.location}"
        elif listing.posted:
            footer = f"Posted {listing.posted}"
        elif listing.location:
            footer = f"Located in {listing.location}"
        else:
            footer = "No location or posted date found."
        embed.set_footer(text=footer)
    return embed

def scrape_url(url: str) -> tuple[Listing, Optional[str]]:
    """
    Scrape a Facebook Marketplace listing for information.
    """
    url = url.split('/?ref')[0]
    listing = Listing(url)
    error = None
    
    try:
        driver = init_webdriver()
        driver.get(url)
        
        try:
            if driver.find_element(By.CSS_SELECTOR, 'div[class="xr1yuqi xkrivgy x4ii5y1 x1gryazu xptc4dh x1l90r2v xyamay9 x4v5mdz xjfs22q"]'):
                error = "Listing not found."
                return listing, error
        except:
            pass
        
        try:
            if driver.find_element(By.CSS_SELECTOR, 'div[class="_9axz"]'):
                error = "Login page encountered while scraping."
                return listing, error
        except:
            pass
        
        listing.title = get_element(
            driver, 
            "title", 
            By.CSS_SELECTOR, 
            'meta[property="og:title"]', 
            lambda x: x.get_attribute('content').replace('\n', ' ')
        )
        listing.description = get_element(
            driver, 
            "description", 
            By.CSS_SELECTOR, 
            'meta[property="og:description"]', 
            lambda x: x.get_attribute('content').replace('\n', ' ')
        )
        listing.price = get_element(
            driver, 
            "price", 
            By.XPATH, 
            '//div[contains(@class, "xckqwgs x26u7qi x2j4hbs x78zum5 xnp8db0 x5yr21d x1n2onr6 xh8yej3 xzepove x1stjdt1")]//div[1]//div[1]//div[1]//*[2]', 
            lambda x: f"${x.text.split("$")[1].split("\u00B7")[0].strip()}", 
            wait=True
        )
        listing.mileage = get_elements(
            driver, 
            "mileage", 
            By.CSS_SELECTOR, 
            'div[class="xamitd3 x1r8uery x1iyjqo2 xs83m0k xeuugli"]', 
            lambda x: re.search(r'([\d,]+)', x[0].text).group(1), 
            wait=True
        )
        listing.location = get_element(
            driver, 
            "location", 
            By.CSS_SELECTOR, 
            'div[class="x78zum5 xl56j7k x1y1aw1k x1sxyh0 xwib8y2 xurb0ha"]', 
            lambda x: x.text.split('\u00B7')[0].strip(),
            wait=True
        )        
        listing.posted =  get_elements(
            driver, 
            "posted", 
            By.CSS_SELECTOR, 
            'span[class="html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x4k7w5x x1h91t0o x1h9r5lt x1jfb8zj xv2umb2 x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1qrby5j"]', 
            lambda x: x[0].text if len(x) == 1 else x[3].text, 
            wait=True
        )
        listing.transmission = get_any(
            get_elements(
                driver, 
                "transmission", 
                By.CSS_SELECTOR, 
                'div[class="xamitd3 x1r8uery x1iyjqo2 xs83m0k xeuugli"]',
                lambda x: x[1].text.split(" ")[0]
            ),
            get_element(
                driver, 
                "transmission", 
                By.CSS_SELECTOR, 
                'div[class="x78zum5 xdj266r x1emribx xat24cr x1i64zmx x1y1aw1k x1sxyh0 xwib8y2 xurb0ha"]', 
                lambda x: x.text.split(" ")[0]
            ),
            validate=lambda x: x in ["Automatic", "Manual"]
        )
        listing.image_url = get_any(
            get_element(
                driver, 
                "image_url", 
                By.CSS_SELECTOR, 
                'img[class="xz74otr x168nmei x13lgxp2 x5pf9jr xo71vjh"]', 
                lambda x: x.get_attribute('src')
            ),
            get_elements(
                driver, 
                "image_url", 
                By.CSS_SELECTOR, 
                'img[class="x1o1ewxj x3x9cwd x1e5q0jg x13rtm0m x5yr21d xl1xv1r xh8yej3"]', 
                lambda x: x[1].get_attribute('src')
            )
        )
        
        return listing, error
    finally:
        driver.quit()

async def send_message(
    message: discord.Message, 
    author: discord.User, 
    url: str, 
    retries: int = RETRY
) -> None:
    """
    Scrape a Facebook Marketplace listing and send the results to the user.
    """
    try:
        embed = build_embed(author)
        
        new_message = await message.channel.send(embed=embed)
        listing, error = await asyncio.to_thread(scrape_url, url)
        if error: raise Exception(error)
        
        listing_embed = update_embed(embed, listing)
        
        if listing.has_key_fields():
            await edit_message_with_retry(new_message, listing_embed)
        elif retries > 0:
            await send_message(new_message, author, url, retries=retries-1)
        else:
            raise Exception("Max retries reached")
    except Exception as e:
        logError(f"An error occurred in send_message: {e}")
        if new_message: await delete_message_with_retry(new_message)
        await author.send(f"An error occurred, but [here's your link back]({url}). Please try again later. ({e})")
