# Mark, a Discord Facebook Marketplace Scraper Bot

Mark is a Discord bot that scrapes information from Facebook Marketplace listings and displays it in a nicely formatted embed within your server.

To invite Mark to your Discord server, click [here.](https://discord.com/oauth2/authorize?client_id=1349283496518221845&permissions=75776&integration_type=0&scope=bot)

## Features

- Scrapes key details from Facebook Marketplace listings:
  - Title
  - Description
  - Price
  - Location
  - Date Posted
  - Main Image
- Provides loading messages while the bot is retrieving data.
- Displays the scraped information as an embed with relevant fields.

## Requirements

### Install Dependencies

1. Clone this repository to your local machine.
2. Install the required packages:

```bash
pip install -r requirements.txt
```

### Set Up Your `.env` File

Create the following `.env` file in the root of the repository:

```env
DB_TOKEN=your_discord_bot_token
GH_TOKEN=your_github_token
```

## Usage

Once you've set up the bot, you can run it using the following command:

```bash
python bot.py
```

## How to Use the Bot

- Simply send a message containing a **Facebook Marketplace** link to the bot in any text channel where the bot has access.
- The bot will scrape the details of the listing and respond with an embed containing:
  - Title
  - Description
  - Price
  - Location
  - Date Posted
  - Image

## Contributing

Feel free to fork this repository and create a pull request if you'd like to contribute improvements or bug fixes.

## License

This project is licensed under the MIT License.
