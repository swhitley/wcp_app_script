import os
import shutil
import subprocess
import json
import logging
import glob
import zipfile
import datetime
import platform
import webbrowser
import time
import sys

# --- Constants ---
################################################################
# Set to the default download directory for your browser.
################################################################
DEFAULT_DOWNLOAD_DIRECTORY = "C:/Users/swhit/Downloads"

WCPCLI_BASE = "wcpcli"
ZIP_EXTENSION = "*.zip"
AMD_SMD_EXTENSIONS = ("./presentation/*.amd", "./presentation/*.smd")
ORCHESTRATE_EXTENSIONS = ("./orchestration/*.orchestration", "./orchestration/*.suborchestration")
DOWNLOAD_TIMEOUT_SECONDS = 60
ARCHIVE_DIRECTORY = "archive"
SRC_DIRECTORY = "src"
# This may need to change for non-US developers.
APP_BUILDER_URI = "https://api.us.developer.workday.com"

# --- Helper Functions ---

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_wcpcli_executable():
    return WCPCLI_BASE + ".cmd" if os.name == 'nt' else WCPCLI_BASE

def run_subprocess_command(command, error_message):
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise Exception(f"{error_message}: {stderr.decode()}")
        return stdout.decode()
    except Exception as e:
        logging.error(f"Error running command '{command}': {e}")
        raise

def validate_directory(directory, error_message):
    if not os.path.exists(directory):
        raise FileNotFoundError(error_message)
    if not os.path.isdir(directory):
        raise NotADirectoryError(error_message)

def get_most_recent_file(directory, pattern):
    search_pattern = os.path.join(directory, pattern)
    matching_files = glob.glob(search_pattern)
    if not matching_files:
        return None
    return max(matching_files, key=os.path.getmtime)

def delete_directory_contents(directory):
    """Deletes all files and folders within a directory, but not the directory itself."""
    validate_directory(directory, f"App directory '{directory}' not found.")
    try:
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            try:
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    os.unlink(filepath)
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            except (OSError, PermissionError) as e:
                logging.error(f"Failed to delete {filepath}. Reason: {e}")
        logging.info(f"Contents of {directory} deleted successfully.")
    except Exception as e:
        logging.error(f"An error occurred during deletion: {e}")
        raise

def extract_zip(zip_filepath, extract_directory):
    """Extracts a zip file to a specified directory."""
    validate_directory(extract_directory, f"Extraction directory '{extract_directory}' not found.")
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(extract_directory)
        logging.info(f"Successfully extracted '{zip_filepath}' to '{extract_directory}'")
    except zipfile.BadZipFile:
        raise Exception(f"'{zip_filepath}' is not a valid zip file.")
    except Exception as e:
        raise Exception(f"An error occurred during zip extraction: {e}")

def rename_file(filepath, new_filename):
    """Renames a file, handling potential errors."""
    try:
        new_filepath = os.path.join(os.path.dirname(filepath), new_filename)
        os.rename(filepath, new_filepath)
        logging.info(f"Renamed '{filepath}' to '{new_filepath}'.")
    except FileExistsError:
        raise Exception(f"File already exists: {new_filepath}")
    except FileNotFoundError:
        raise Exception(f"File not found: {filepath}")
    except Exception as e:
        raise Exception(f"Failed to rename '{filepath}': {e}")

def move_file(source_filepath, dest_directory):
    """Moves a file to a destination directory."""
    validate_directory(dest_directory, f"Destination directory '{dest_directory}' not found.")
    try:
        shutil.move(source_filepath, dest_directory)
        logging.info(f"Moved '{source_filepath}' to '{dest_directory}'")
    except Exception as e:
        raise Exception(f"Failed to move '{source_filepath}' to '{dest_directory}': {e}")

def authenticate_wcpcli():
    """Authenticates with wcpcli."""
    command = [get_wcpcli_executable(), "auth:login"]
    try:
        run_subprocess_command(command, "WCPCLI login failed")
        logging.info("WCPCLI login successful.")
    except Exception as e:
        raise Exception(f"WCPCLI Authentication failed: {e}")

def fetch_application_id(reference_id):
    """Fetches the application ID from wcpcli given a reference ID."""
    command = [get_wcpcli_executable(), "apps:list"]
    try:
        stdout_str = run_subprocess_command(command, "Failed to fetch apps list")
        first_newline = stdout_str.find('\n')
        if first_newline == -1:
            print(f"Failed to fetch json list: {stderr.decode()}")
        stdout_str = stdout_str[first_newline + 1:]         
        if not stdout_str:
            raise Exception("Empty response from wcpcli apps:list")
        apps_data = json.loads(stdout_str)
        for app in apps_data:
            if app.get("referenceId") == reference_id:
                app_id = app.get("id")
                logging.info(f"Found application ID: {app_id}")
                return app_id
        raise Exception(f"Application with referenceId '{reference_id}' not found.")
    except json.JSONDecodeError:
        raise Exception("Error decoding JSON response from wcpcli apps:list")

def download_source_archive(app_id, download_directory):
    """Downloads the source archive for a given application ID."""
    source_url = APP_BUILDER_URI + "/devtools/v1/appbuilder/" + app_id + "/source/archive"
    logging.info(f"Downloading source archive from: {source_url}")

    try:
        # Get the most recent file in the download directory.
        most_recent_file = get_most_recent_file(download_directory, ZIP_EXTENSION)

        webbrowser.open(source_url)
        start_time = time.time()
        downloaded_file = None

        while time.time() - start_time < DOWNLOAD_TIMEOUT_SECONDS:
            downloaded_file = get_most_recent_file(download_directory, ZIP_EXTENSION)
            if downloaded_file and (not most_recent_file or os.path.basename(most_recent_file) != os.path.basename(downloaded_file)):
                logging.info(f"Download complete: {downloaded_file}")
                return downloaded_file
            time.sleep(1)

        raise Exception(f"Download timed out after {DOWNLOAD_TIMEOUT_SECONDS} seconds.")

    except Exception as e:
        raise Exception(f"Error downloading source archive: {e}")

def process_download(downloaded_file, src_directory, archive_directory):
    """Processes the downloaded archive: deletes old content, extracts, and renames files."""

    if not downloaded_file:
        raise ValueError("No downloaded file provided for processing.")

    logging.info(f"Deleting old files.")
    delete_directory_contents(src_directory)

    logging.info(f"Moving the downloaded file to the archive.")
    move_file(downloaded_file, archive_directory)
    
    logging.info(f"Renaming the source zip file.")
    archive_filepath = os.path.join(archive_directory, os.path.basename(downloaded_file))
    archive_filepath = rename_archive(archive_filepath, archive_directory)

    logging.info(f"Unzipping the source file.")
    extract_zip(archive_filepath, src_directory)

    logging.info(f"Renaming amd and smd files.")
    rename_amd_smd_files(src_directory)
    
    logging.info(f"Pretty printing orchestration files.")
    pretty_print_orchestrations(src_directory)
    

def rename_amd_smd_files(directory, extensions=AMD_SMD_EXTENSIONS):
    """Renames .amd and .smd files in a directory."""

    def generate_new_filename(base_name, file_extension):
        metadata = 'metadata'
        if file_extension == '.amd':
            metadata = 'application_metadata'
        if file_extension == '.smd':
            metadata = 'site_metadata'
        company_code = 'xxxxxx'
        parts = base_name.rsplit('_', 1)
        if len(parts) != 2:
            raise ValueError(f"Filename '{base_name}' does not contain an underscore to split on.")
        return f"{metadata}_{company_code}{file_extension}"

    for extension_pattern in extensions:
        pattern = os.path.join(directory, extension_pattern)
        matching_files = glob.glob(pattern)

        for filepath in matching_files:
            try:
                directory_path, filename = os.path.split(filepath)
                base_name, file_extension = os.path.splitext(filename)
                new_filename = generate_new_filename(base_name, file_extension)
                rename_file(filepath, new_filename)
            except Exception as e:
                logging.error(f"Failed to rename '{filepath}': {e}")

def pretty_print_orchestrations(directory, extensions=ORCHESTRATE_EXTENSIONS):
    """Pretty Prints Orchestration Files"""

    for extension_pattern in extensions:
        pattern = os.path.join(directory, extension_pattern)
        matching_files = glob.glob(pattern)

        for filepath in matching_files:
            try:
                # Read the file content
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Try to parse and pretty-print as JSON
                try:
                    parsed_json = json.loads(content)
                    pretty_content = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                    
                    # Write the pretty-printed content back to the same file
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(pretty_content)
                    
                    logging.info(f"Pretty-printed orchestration file: {filepath}")
                    
                except json.JSONDecodeError as json_error:
                    logging.warning(f"File '{filepath}' is not valid JSON, skipping pretty-print: {json_error}")
                    
            except Exception as e:
                logging.error(f"Failed to pretty-print '{filepath}': {e}")                
                

def rename_archive(filepath, archive_directory):
    """Moves the file to the archive directory."""

    dt_string = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name, file_extension = os.path.splitext(os.path.basename(filepath))
    new_filename = f"{base_name}_{dt_string}{file_extension}"
    new_filepath = os.path.join(archive_directory, new_filename)

    rename_file(filepath, new_filepath)
    
    return new_filepath

def wcp_app_download(reference_id, app_directory, download_directory):
    """
    Downloads source files from developer.workday.com with wcpcli.
    """
    setup_logging()  # Initialize logging

    try:
        validate_directory(download_directory, f"Download directory '{download_directory}' not found.")
        validate_directory(app_directory, f"App directory '{app_directory}' not found.")
        src_directory = os.path.join(app_directory, SRC_DIRECTORY)
        archive_directory = os.path.join(app_directory, ARCHIVE_DIRECTORY)        
        
        try:            
            validate_directory(src_directory, f"Src directory '{src_directory}' not found. Creating Src directory.")
        except Exception as e:
            os.makedirs(src_directory)
        try:            
            validate_directory(archive_directory, f"Archive directory '{archive_directory}' not found. Creating Archive directory.")
        except Exception as e:
            os.makedirs(archive_directory)

        authenticate_wcpcli()
        app_id = fetch_application_id(reference_id)
        downloaded_file = download_source_archive(app_id, download_directory)

        if downloaded_file:
            process_download(downloaded_file, src_directory, archive_directory)
  
        logging.info(f"App download complete.")  
            

    except FileNotFoundError as e:
        logging.error(f"Required tool or directory not found: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)  # Log with traceback

   
if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python wcp_app_download.py <reference_id> <app_directory> [<download_directory>]")
        sys.exit(1)

    reference_id_to_lookup = sys.argv[1]
    if reference_id_to_lookup.startswith("wcp_"):
        reference_id_to_lookup = reference_id_to_lookup[4:]
    app_directory = sys.argv[2]

    if len(sys.argv) == 4:
        download_directory = sys.argv[3]  # Override with command-line argument
    else:
        download_directory = DEFAULT_DOWNLOAD_DIRECTORY # Use the default if not provided

    wcp_app_download(reference_id_to_lookup, app_directory, download_directory)
