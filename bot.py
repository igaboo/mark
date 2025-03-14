import re, os, asyncio, random
from dotenv import load_dotenv
import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

# silly loading messages in relation to facebook marketplace cars
LOADING_MESSAGES = [
    "Checking the oil...",
    "Haggling with the seller...",
    "Checking the carfax...",
    "Test driving the car...",
    "Negotiating the price...",
    "Taking out a loan...",
    "Thinking about it...",
    "Checking the tires...",
    "Looking for scratches...",
    "Imagining driving it...",
]

# set timeout time for selenium
TIMEOUT_TIME = 10

# load env
load_dotenv()

# apply token from env to os so webdriver can access it
os.environ['GH_TOKEN'] = os.getenv('GH_TOKEN')

# setup discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, )

# initialize driver
def init_driver():
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    return driver

# scrape marketplace link
def scrape(url):
    # clean the url
    if '/?ref' in url: url = url.split('/?ref')[0]

    # setup firefox driver
    driver = init_driver()
    
    try:
        driver.get(url)
        
        result = {
            'title': None, 
            'price': None, 
            'description': None, 
            'image_url': None, 
            'location': None, 
            'mileage': None, 
            'transmission': None, 
            'posted': None,
        }
        error = None
        
        # if the class "_9axz" exists a login page was encountered, abort
        try:
            if driver.find_element(By.CSS_SELECTOR, 'div[class="_9axz"]'):
                error = "Login page encountered!"
                return result, error
        except:
            pass

        try:
            result["title"] = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:title"]'))
            ).get_attribute('content').replace('\n', ' ')
        except Exception as e:
            print(f"Error scraping title: {e}")

        try:
            result["description"] = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:description"]'))
            ).get_attribute('content').replace('\n', ' ')
        except Exception as e:
            print(f"Error scraping description: {e}")

        try:        
            price = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'xckqwgs x26u7qi x2j4hbs x78zum5 xnp8db0 x5yr21d x1n2onr6 xh8yej3 xzepove x1stjdt1')]//div[1]//div[1]//div[1]//*[2]"))
            ).text.split("$")[1].split("·")[0].strip()
            result["price"] = f"${price}"
        except Exception as e:
            print(f"Error scraping price: {e}")

        try:
            result["location"] = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[class="x193iq5w xeuugli x13faqbe x1vvkbs xlh3980 xvmahel x1n0sxbx x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x xudqn12 x3x7a5m x6prxxf xvq8zen x1s688f x1fey0fg"]'))
            ).text.split('·')[0].strip()
        except Exception as e:
            print(f"Error scraping location: {e}")

        try:
            elements = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[class="xamitd3 x1r8uery x1iyjqo2 xs83m0k xeuugli"]'))
            )
            result["mileage"] = re.search(r'([\d,]+)', elements[0].text).group(1)
            result["transmission"] = elements[1].text.split(" ")[0]
        except Exception as e:
            print(f"Error scraping mileage: {e}")
            try: # transmission might also be under a different class
                result["transmission"] = driver.find_element(By.CSS_SELECTOR, 'div[class="x78zum5 xdj266r x1emribx xat24cr x1i64zmx x1y1aw1k x1sxyh0 xwib8y2 xurb0ha"]').text.split(" ")[0]
            except Exception as e:
                print(f"Error scraping transmission: {e}")

        try:
            posted_elements = WebDriverWait(driver, TIMEOUT_TIME).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span[class="html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x4k7w5x x1h91t0o x1h9r5lt x1jfb8zj xv2umb2 x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1qrby5j"]'))
            )
            result["posted"] = posted_elements[0].text if len(posted_elements) == 1 else posted_elements[3].text
        except Exception as e:
            print(f"Error scraping posted date: {e}")

        try:
            result["image_url"] = driver.find_element(By.CSS_SELECTOR, 'img[class="xz74otr x168nmei x13lgxp2 x5pf9jr xo71vjh"]').get_attribute('src')
        except: # first image is a video, get the second image
            try:
                result["image_url"] = driver.find_elements(By.CSS_SELECTOR, 'img[class="x1o1ewxj x3x9cwd x1e5q0jg x13rtm0m x5yr21d xl1xv1r xh8yej3"]')[1].get_attribute('src')
            except Exception as e:
                print(f"Error scraping image: {e}")

        return result, error
    finally:
        driver.quit()

# fetch data in a separate thread
async def fetch_data(url):
    return await asyncio.to_thread(scrape, url)

# listen for messages containing a marketplace link
@bot.event
async def on_message(message):
    if message.author == bot.user: return

    # check if message contains a marketplace link
    pattern = r'https://www\.facebook\.com/marketplace/[^\s]+'
    urls = re.findall(pattern, message.content)
    
    if urls:
        try:
            # delete the original message and send a loading message
            await message.delete()
            embed = discord.Embed(description=random.choice(LOADING_MESSAGES), color=0x1877f2)
            embed.set_author(name=f"Look what {message.author.name} found!", icon_url=message.author.avatar)
            sent = await message.channel.send(embed=embed)
            
            # scrape the link
            result, error = await fetch_data(urls[0])
            title, price, description, image_url, location, mileage, transmission, posted = result.values()
            
            # if an error occurred, send the error message
            if error:
                await sent.edit(content=f"An error occurred, but [here's your link back]({urls[0]}).", embed=None)
                return
            
            # update the embed with the scraped data
            embed.title = title
            embed.description = description
            embed.url = urls[0]
            if price: embed.add_field(name='Price', value=price, inline=True)
            if mileage: embed.add_field(name='Mileage', value=mileage, inline=True)
            if transmission: embed.add_field(name='Transmission', value=transmission, inline=True)
            if image_url: embed.set_image(url=image_url)
            
            # build the footer
            footer = None
            if posted and location:
                footer = f"Posted {posted} in {location}"
            elif posted:
                footer = f"Posted {posted}"
            elif location:
                footer = f"Located in {location}"
            if footer: embed.set_footer(text=footer)
            
            # send the edited embed
            await sent.edit(content='', embed=embed)
        except Exception as e:
            print(f"An error occurred: {e}")
            if sent: await sent.delete()
            await message.channel.send(f"An error occurred, but [here's your link back]({urls[0]}).")

    await bot.process_commands(message)

# start the bot
bot.run(os.getenv('DB_TOKEN'))