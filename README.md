# WCP App Script
This script is designed to automate the process of downloading an application from Workday's App Hub.  It facilitates source code management when not using an IDE such as Intellij.

## Steps Performed by the Script
1. Authenticate to App Hub using `auth:login` with WCPCLI.
2. Get a list of applications using `apps:list` with WCPCLI.
3. Lookup the Application Id for an application using the Application's Reference Id.
4. Download the application's source archive (ZIP file) using the Application Id.
5. Rename the source archive by date/time and place the file in an archive directory.
6. Delete any old files in the src directory.
7. Extract the downloaded files to the src directory.
8. Rename the application metadata file and site metadata file (.amd and .smd) for convenient comparison to versions of the application that may have a different reference id.

It is recommended for the src directory to be used for source code management.  The process has been tested with GitHub where the src directory is the location of the local repository.

## Script Installation
1. Install WCPCLI using the standard installation for your os.  Note that this script has been primarily tested on Windows.  https://developer.workday.com/documentation/nmq1528733132785/GetStartedwiththeWorkdayCloudPlatformCLI
2. A default company is recommended. Set a default company using the WCPCLI instructions.  To locate the code, on developer.workday.com, click *Account* and location your *Organization Short Id*.

Example: `wcpcli config:set defaultCompanyShortId xxxxxx`

3. Place the file, wcp_app_script.py, in the WCPCLI /bin directory.  On Windows, the default is `C:\Program Files\Workday\wcpcli\bin`
4. Edit the file, wcp_app_script.py, with your favorite text editor and set the DEFAULT_DOWNLOAD_DIRECTORY to your browser's default download directory.
5. Follow the steps below for any application that uses this script.

## New Application Installation
1. Create an application directory that will hold your src and archive directories.
2. For Windows users, place the file, wcp_app_script.cmd, in your application directory.
3. Update wcp_app_script.cmd and enter the Application's Reference Id in APP_REFERENCE_ID.
4. If you are not using Windows, you can create a similar command script or enter the commands on the command line.
5. Before executing the script, make sure you are signed on to developer.workday.com.  The script opens a browser window and relies on your existing signon.
6. Windows users can double-click the file, wcp_app_script.com, to execute the commands.
7. You can also run the script from the command line:

`"{wcpcli bin directory}\wcp_app_script.py" "{application reference id}" "{current application directory}"`

Example:  `"C:\Program Files\Workday\wcpcli\bin\wcp_app_script.py" "positionmanagement_xzkyht" "C:\Workday_Extend\positionmanagement_xzkyht"`

   
