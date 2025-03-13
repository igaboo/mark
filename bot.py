import re, os, asyncio, time
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

# set timeout time for selenium
timeout_time = 5

# silly loading messages in relation to facebook marketplace cars
loading_messages = [
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

# load env
load_dotenv()

# apply token from env to os so webdriver can access it
os.environ['GH_TOKEN'] = os.getenv('GH_TOKEN')

# setup discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, )

# scrape marketplace link
def scrape(url):
    # if url has /?ref then remove it and all that follows
    if '/?ref' in url: url = url.split('/?ref')[0]

    # setup firefox driver
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        time.sleep(3) # wait for page to load

        try: # scrape the title
            title = WebDriverWait(driver, timeout_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:title"]'))
            ).get_attribute('content').replace('\n', ' ')
        except:
            title = "Unknown Title"
        try: # scrape the description  
            description = WebDriverWait(driver, timeout_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:description"]'))
            ).get_attribute('content').replace('\n', ' ')
        except:
            description = "Unknown Description"
        try: # scrape the price            
            price = WebDriverWait(driver, timeout_time).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'xckqwgs x26u7qi x2j4hbs x78zum5 xnp8db0 x5yr21d x1n2onr6 xh8yej3 xzepove x1stjdt1')]//div[1]//div[1]//div[1]//*[2]"))
            ).text.split("$")[1].split("·")[0].strip()
            price = f"${price}"
        except:
            price = "Unknown Price"
        try: # scrape the location 
            location = WebDriverWait(driver, timeout_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[class="x193iq5w xeuugli x13faqbe x1vvkbs xlh3980 xvmahel x1n0sxbx x1lliihq x1s928wv xhkezso x1gmr53x x1cpjm7i x1fgarty x1943h6x xudqn12 x3x7a5m x6prxxf xvq8zen x1s688f x1fey0fg"]'))
            ).text.split('·')[0].strip()
        except:
            location = "Unknown Location"
            
        try: # scrape the date posted
            posted_elements = WebDriverWait(driver, timeout_time).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span[class="html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs x4k7w5x x1h91t0o x1h9r5lt x1jfb8zj xv2umb2 x1beo9mf xaigb6o x12ejxvf x3igimt xarpa2k xedcshv x1lytzrv x1t2pt76 x7ja8zs x1qrby5j"]'))
            )
            
            if len(posted_elements) == 1:
                posted = posted_elements[0].text
            else:
                posted = posted_elements[3].text
        except:
            posted = "Unknown date"
        try: # scrape the main image
            image_url = driver.find_element(By.CSS_SELECTOR, 'img[class="xz74otr x168nmei x13lgxp2 x5pf9jr xo71vjh"]').get_attribute('src')
        except: # first image is a video, get the second image
            try:
                image_url = driver.find_elements(By.CSS_SELECTOR, 'img[class="x1o1ewxj x3x9cwd x1e5q0jg x13rtm0m x5yr21d xl1xv1r xh8yej3"]')[1].get_attribute('src')
            except:
                image_url = "https://media.istockphoto.com/id/1162198273/vector/question-mark-icon-flat-vector-illustration-design.jpg?s=612x612&w=0&k=20&c=MJbd8bw2iewJRd8sEkHxyGMgY3__j9MKA8cXvIvLT9E="
        
        return title, price, description, image_url, location, posted
    finally:
        driver.quit()

# listen for messages containing a marketplace link
@bot.event
async def on_message(message):
    if message.author == bot.user: return

    # check if message contains a marketplace link
    pattern = r'https://www\.facebook\.com/marketplace/[^\s]+'
    urls = re.findall(pattern, message.content)
    
    if urls:
        try:
            # delete the original message
            await message.delete()
            
            # send an empty embed to edit later
            embed = discord.Embed(description='Loading...', color=0x1877f2)
            embed.set_author(name=f"Look what {message.author.name} found!", icon_url=message.author.avatar)
            
            sent = await message.channel.send(embed=embed)
            
            # loop through loading messages
            async def update_loading_messages():
                while True:
                    for message in loading_messages:
                        embed.description = message
                        await sent.edit(content='', embed=embed)
                        await asyncio.sleep(2)
            loading_task = asyncio.create_task(update_loading_messages())
            
            # run scrape() in a separate thread to prevent blocking
            title, price, description, image_url, location, posted = await asyncio.to_thread(scrape, urls[0])
            
            # cancel the loading messages
            loading_task.cancel()
            
            embed.title = title
            embed.description = description
            embed.url = urls[0]
            embed.add_field(name='Price', value=price, inline=True)
            embed.add_field(name='Location', value=location, inline=True)
            embed.add_field(name='Posted', value=posted, inline=True)
            embed.set_thumbnail(url=image_url)
            
            await sent.edit(content='', embed=embed)
        except Exception as e:
            print(f'An error occurred in the @bot.event block: {e}')
            await sent.delete()
            await message.channel.send(f"An error occurred, but here's your link back: {urls[0]}")

    await bot.process_commands(message)

# start the bot
bot.run(os.getenv('DB_TOKEN'))