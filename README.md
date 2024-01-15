# DCS Server Logbook

## Description

The DCS Server Logbook is a comprehensive tool designed for enhancing the experience of managing and tracking activities in Digital Combat Simulator (DCS) servers. This updated version integrates Discord bot functionality, Python scripting, and SQLite database management, offering a more interactive and user-friendly interface for server administrators and pilots.

## Key Features

- **Discord Integration**: Utilizes a Discord bot (`bot.py`) for interactive management and queries, enhancing user engagement.
- **Comprehensive Data Management**: Processes and stores data in an SQLite database, ensuring efficient handling of server and pilot information.
- **Dynamic HTML Report Generation**: Generates detailed HTML reports for pilots and squadrons, providing insights into performance and activities.
- **Automated Data Processing**: `main.py` includes functions like `process_combined_data` and `run_lua_script` to handle data parsing and processing.
- **Pilot and Squadron Management**: Features in `bot.py` such as `add_squadron`, `assign_pilot`, and `update_logbook` offer robust management capabilities.
- **Award and Qualification Tracking**: Functions like `create_award`, `give_qualification`, and `clear_award` facilitate tracking and management of pilot achievements.

## File Structure

- `main.py`: The core script for data processing and report generation.
- `bot.py`: Discord bot script for interaction and management.
- `html_generator/`: Module for generating HTML reports.
- `utils/`: Utility scripts for statistical processing and other functions.
- `database/`: Contains database management scripts and SQLite database.
- `config.py`: Configuration file for setting paths and tokens.

## Setup

1. Ensure Python and Discord.py are installed on your system.
2. Set up an SQLite database on your server.
3. Clone the repository:

   ```
   git clone https://github.com/engines-wafu/dcs_server_logbook.git
   ```

4. Install required Python packages:

   ```
   pip install -r requirements.txt
   ```

5. Configure `config.py` with your Discord bot token and other preferences.
6. Invite the Discord bot to the server and give it the necessary permissions including:
  a. View channels
  b. Manage roles
  c. Send messages
  d. Manage messages
  e. Read message history

## Usage

1. Run the Discord bot:

   ```
   python src/bot.py
   ```

2. Use bot commands for managing pilots, squadrons, and generating reports.
3. For data processing, execute `main.py`:

   ```
   python src/main.py
   ```

## Customization

- Modify `bot.py` for custom Discord bot commands and interactions.
- Update `main.py` for specific data processing requirements.
- Extend HTML report templates within the `html_generator` module for personalized report layouts.

## Contributing

Contributions are welcome to further enhance the functionality of DCS Server Logbook:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Commit and push your changes.
4. Submit a pull request to the main repository.

## License

This project is licensed under the GNU General Public License (GPL). For more information, please refer to the [LICENSE](LICENSE) file in the repository.
