from io import BytesIO, StringIO
import os
from auth import require_auth
import uuid
import shutil
import zipfile
from db import get_db_instance
import server_conf  # Import your configuration file
from quart import Quart, Response, request, send_file, jsonify,abort, Blueprint, current_app, g
from datetime import datetime, timezone
from messages import USER_MESSAGES
from utils import validate_experiment_name, validate_experiment_tags, validate_redirect_url
from shutil import rmtree
import json
import csv
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from users import get_user_by_id, get_all_users, get_user_by_query_params

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=True
)


PORT = server_conf.PORT
PRIVATE_DIRECTORY = server_conf.PRIVATE_DIRECTORY
PUBLIC_DIRECTORY = server_conf.PUBLIC_DIRECTORY
SOURCE_FILE_DIRECTORY = server_conf.SOURCE_ZIP_DIRECTORY
BASE_APPLICATION_URL = server_conf.BASE_APPLICATION_URL
PWD = os.getcwd()  # Define PWD dynamically or from config
IBEX_WORKING_DIR = os.path.abspath(server_conf.IBEX_WORKING_DIR)
CHUNK_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.CHUNK_INCLUDES_DIR)
CSS_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.CSS_INCLUDES_DIR)
DATA_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.DATA_INCLUDES_DIR)
JS_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.JS_INCLUDES_DIR)   
HTML_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.STATIC_FILES_DIR)   
EXPECTED_FOLDERS = server_conf.EXPECTED_FOLDERS

experiments_routes = Blueprint('experiments', __name__)
def get_experiment_collection_instance():
    client = get_db_instance()
    mongo_db = client[os.getenv('MONGO_DB')]
    experiments_collection = mongo_db['experiments']
    return experiments_collection

async def create_experiment_entry(payload):
    return await get_experiment_collection_instance().insert_one(payload)

async def get_experiment_entry_by_query(query):
    experiment_collection = get_experiment_collection_instance()
    return await experiment_collection.find_one(query)
    
async def get_experiment_entry_by_name(experiment_name):
    return await get_experiment_entry_by_query({'name': experiment_name})

async def get_experiment_entry_by_id_and_user(experiment_id, user_id):
    return await get_experiment_entry_by_query({'_id': experiment_id, 'created_by': user_id})

async def get_experiment_entry_by_id(experiment_id):
    return await get_experiment_entry_by_query({'_id': experiment_id})

async def delete_experiment_entry(experiment_id):
    experiment_collection = get_experiment_collection_instance()
    deleted = await experiment_collection.delete_one({'_id': experiment_id})
    return deleted.deleted_count > 0

async def get_all_experiments_entries(search=None):
    """ 
        This function returns all the experiment entries from the DB. 
        If a search query is provided, it queries the database for experiments whose name matches the search query,
        or the experiment creater's name.
    """
    query = {}
    if search:
        users = await get_user_by_query_params(search)

        user_ids = [u["_id"] for u in users]

        query = {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"created_by": {"$in": user_ids}}
            ]
        }
    experiment_collection = get_experiment_collection_instance()
    return await experiment_collection.find(query).to_list(None)

def processResultFile(file_path):
    """
        Each file is a of the following format:
        [
            false,           # arr[0] (not used)
            5,                   # counter
            ["colA", "colB", ...], # list of column names mapping to 'columnNamesArray' from other_includes/main.js 
            [
                [0, "val_for_colA"],
                [1, "val_for_colB"],
                        ...
            ]                    # arr[3] = row data (list of [colIndex, value]) mapping to 'resultsLines' from other_includes/main.js 
        ]
                
        We need to extract the counter, column names and map the row data to the appropriate column names.
        This function does that job!         
    """
    output_buffer = StringIO()
    with open(file_path, "r", encoding="utf-8") as file:
        writer = None
        for line in file:
            # Parse the JSON array from the line
            arr = json.loads(line.strip())
            counter = arr[1]
            colnames = arr[2]
            rowdata = arr[3]
            
            for entry in rowdata:
                # Map col index and values to those columns for better lookup
                row_dict = {col_idx: value for col_idx, value in entry}
                
                # Map the column names from arr[2] to row data
                row_output = {col_name: row_dict.get(idx, "") for idx, col_name in enumerate(colnames)}
            
                # Add counter to the row output by introdcuing a new column called "counter"
                row_output["counter"] = counter
            
                # Create CSV writer with header only once
                if writer is None:
                    header = colnames + ["counter"]
                    writer = csv.DictWriter(output_buffer, fieldnames=header)
                    writer.writeheader()

                writer.writerow(row_output)
            
    return output_buffer.getvalue()

    
def create_sub_folders_in_ibex(experiment_name):
    """ 
        This helper function creates the necessary folders to store the zip file contents of an experiment
    """
    for folder_name in EXPECTED_FOLDERS:
        folder_path = Path(PUBLIC_DIRECTORY) / folder_name / experiment_name
        folder_path.mkdir(exist_ok=True) 
        
async def delete_experimental_files_and_folders(experiment_name):
    """ 
        This function deletes all the files and folders associated with an experiment.
    """
    # First delete all static files of experiment
    for folder_name in EXPECTED_FOLDERS:
        folder_path = Path(PUBLIC_DIRECTORY) / folder_name / experiment_name
        print(folder_path.exists())
        if folder_path.exists() and folder_path.is_dir():
            shutil.rmtree(folder_path)
            
    # Now delete the index.html from www
    index_file_path = Path(PUBLIC_DIRECTORY) / "www" / experiment_name
    if index_file_path.exists() and index_file_path.is_dir():  
        shutil.rmtree(index_file_path)
        
    # Now delete the counter files and results file
    results_dir_path = Path(PUBLIC_DIRECTORY) / "results" / experiment_name 
    if results_dir_path.exists() and results_dir_path.is_file():
        shutil.rmtree(results_dir_path)
    
def create_results_and_www_folders(experiment_name):
    """ 
        This function creates the results and counter files, as well as the index.html for the experiment
    """
    # Now add index.html to the experiment folder 
    write_experiment_html(experiment_name)
    
    # Add the results and counter files 
    results_dir = Path(PUBLIC_DIRECTORY) / "results" / experiment_name
    results_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = results_dir / "results"
    results_file.touch(exist_ok=True) # Just create, but not write anything.
    
    counter_file = results_dir / "counter"
    counter_file.write_text("0", encoding="utf-8") # Initialise the counter to 0
    
async def extract_and_organize_zip(zip_file_path, experiment_name): 
    """
        This function extracts the uploaded zip file, and organizes the files into appropriate 
        directories based on the expected structure of the zip file.
    Args:
        zip_file_path (str): (Temperory) Path to the uploaded zip file
        experiment_name (str): The name of the experiment to which the uploaded zip file is associated with.

    Returns:
        tuple: A tuple containing a boolean indicating the success of extracting and organizing the zip file contents, 
               and a message associated with this operation.
    """
    try:
        # Validate zip file
        if not zipfile.is_zipfile(zip_file_path):
            return False, "Invalid ZIP File"
        
        # Extract zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(file_list)
            for file_name in file_list:
                # Skip directories and hidden files
                if file_name.endswith('/') or os.path.basename(file_name).startswith('.'):
                    continue
                
                # Parse the file path
                file_path = Path(file_name)
                parts = file_path.parts
                # print(parts)
                # Determine target folder
                target_folder = None
                if len(parts) == 2 and parts[0] in EXPECTED_FOLDERS: 
                    for folder in EXPECTED_FOLDERS:
                        if folder in parts:
                            target_folder = folder
                            break
                    
                    if target_folder:
                        # Calculate the relative path within the target folder
                        try:
                            folder_index = parts.index(target_folder)
                            # Get everything after the target folder name
                            relative_parts = parts[folder_index + 1:]
                            
                            if relative_parts:
                                relative_path = Path(*relative_parts)
                            else:
                                # File is directly in the folder
                                relative_path = file_path.name
                            
                            # Create full destination path
                            dest_path = Path(PUBLIC_DIRECTORY) / target_folder / experiment_name / relative_path
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            
                            # Extract file directly to destination
                            with zip_ref.open(file_name) as source:
                                with open(dest_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)       
                        except:
                            return False, "Error processing file paths from ZIP file"
                        
                    else: 
                        return False, f"File {file_name} is not in an expected folder"
        return True, "Files extracted successfully"    
    except:
        return False, "Error processing file paths from ZIP file"
    

def write_experiment_html(experiment_name):
    """
        This function writes the index.html file for the experiment in the www folder by 
        populating the correct values based on the template available in template.html file
    """
    template = jinja_env.get_template("template.html")

    html = template.render(
        experiment_name=experiment_name,
        has_global_z_css=(
            Path(PUBLIC_DIRECTORY)
            / "css_includes"
            / experiment_name
            / "global_z.css"
        ).is_file(),
    )

    output_dir = Path(PUBLIC_DIRECTORY) / "www" / experiment_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "index.html"
    output_file.write_text(html, encoding="utf-8")

    return str(output_file)


@experiments_routes.route('/', methods=['POST'])
@require_auth
async def create_experiment():
    """ 
        This route creates a new experiment based on the payload (containing the experiment name, tags, redirect URL
        and the zip file associated with the experiment).
    """
    experiment_data = await request.form
    files = await request.files
    
    # Validate the payload
    if not experiment_data or not 'name' in experiment_data:
        return jsonify(USER_MESSAGES["INVALID_EXPERIMENT_PAYLOAD"]), 400
    
    experiment_name = experiment_data['name'].strip()
    valid, message = validate_experiment_name(experiment_name)
    if not valid:
        return jsonify(message), 400
    tags = experiment_data.get('tags')
    if len(tags) > 0:
        tags_list = [tag.strip() for tag in tags.split(',')]
    else:
        tags_list = []
        
    if len(tags_list) > 0:
        valid_tags, message = validate_experiment_tags(tags_list)
        if not valid_tags:
            return jsonify(message), 400
    
    redirect_url = experiment_data['redirect_url'].strip() if 'redirect_url' in experiment_data else None
    valid, message = validate_redirect_url(redirect_url)
    if not valid:
        return jsonify(message), 400
    
    # Get the uploaded file
    if 'file' not in files:
        return jsonify(USER_MESSAGES["NO_FILE_UPLOADED"]), 400
    
    uploaded_file = files['file']
    
    # Validate file
    if not uploaded_file or uploaded_file.filename == '':
        return jsonify(USER_MESSAGES["NO_FILE_UPLOADED"]), 400
    
    if not uploaded_file.filename.lower().endswith('.zip'):
        return jsonify(USER_MESSAGES["INVALID_FILE_TYPE"]), 400
    
    # Save uploaded zip file
    source_zip_path = Path(SOURCE_FILE_DIRECTORY) / f"temp_{experiment_name}.zip"
    await uploaded_file.save(str(source_zip_path))
    
    if not source_zip_path.exists() or source_zip_path.stat().st_size == 0:
        return jsonify(USER_MESSAGES["SOURCE_ZIP_SAVE_FAILED"]), 500
    
    # Check if the experiment exists in DB
    experiment_exists = await get_experiment_entry_by_name(experiment_name)
    if experiment_exists:
        index_file_path = Path(PUBLIC_DIRECTORY) / "www" /experiment_name/"index.html"
        if index_file_path.exists(): # What if the file is deleted but the entry exists?
            return jsonify(USER_MESSAGES["EXPERIMENT_EXISTS"]), 200
        else:
            # The entry exists somehow but the files don't.
            # How did this happen?
            # Nvm, let me just delete the entry from DB
            deleted = await delete_experiment_entry(experiment_exists['_id'])
            if not deleted:
                # Weird, what's happening in MongoDB?
                # Handle this later.
                print("Hi")          
    
    # Automatic creation of directories and files from the zip file contents
    file_saved, message = await extract_and_organize_zip(
            source_zip_path, experiment_name
    )
      
    if not file_saved:
        source_zip_path.unlink(missing_ok=True)  # Remove temp file
        return jsonify({"error": message}), 400
    
    create_results_and_www_folders(experiment_name)
    
    # Create the entry into DB
    now_utc = datetime.now(timezone.utc)
    epochs_ms = int(now_utc.timestamp() * 1000)    
    experiment_data = {
        "_id": str(uuid.uuid4()), 
        "created_by": g.user_id,
        "name": experiment_name,
        "tags": tags_list,
        "redirect_url": redirect_url,
        "created_at": epochs_ms,
        "last_edited": epochs_ms
    }
    
    result = await create_experiment_entry(experiment_data)
    if not result:
        # First delete all the files and directories that were created.
        await delete_experimental_files_and_folders(experiment_name)
        return jsonify(USER_MESSAGES["EXPERIMENT_CREATE_FAILED"]), 500
    
    else:
        return jsonify(USER_MESSAGES["EXPERIMENT_CREATED"]), 201

@experiments_routes.route('/', methods=['GET'])
@require_auth
async def get_items():
    """ 
        This route returns the list of experiments created by the user, along with some metadata like creation date, 
        last edited date and a link to the experiment. This route also accepts an optional search query parameter to filter the experiments.
    """
    try:
        search = request.args.get("search", "").strip()
        if search:
            all_experiments_from_db = await get_all_experiments_entries(search=search)
        else:
            all_experiments_from_db = await get_all_experiments_entries()
        if not all_experiments_from_db:
            return jsonify({"items": []}), 200
        items = []

        all_users = await get_all_users()
        user_lookup = {user["_id"]: user["full_name"] for user in all_users}
        for experiment in all_experiments_from_db:
            if os.path.isdir(os.path.join(PRIVATE_DIRECTORY, experiment['name'])):
                items.append({
                    "experiment": experiment['name'],
                    "created_by": experiment['created_by'],
                    "created_user": user_lookup.get(experiment['created_by'], "Deleted User"),
                    "_id": experiment['_id'],
                    "publish_link": f"{BASE_APPLICATION_URL}/www/{experiment['name']}/index.html",
                    "last_edited": datetime.fromtimestamp(experiment['last_edited']/1000).strftime("%Y-%m-%d %H:%M:%S")
                })
        return jsonify({"items": items}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@experiments_routes.route('/erase/<experiment_id>', methods=['DELETE'])
@require_auth
async def erase_experiment_results(experiment_id):
    """ 
        This route erases the result file contents of an experiment based on the experiment ID. 
        This is useful when the experimenter wants to erase the experiment results from test run 
        and then publish the experiment in Prolific.
    """
    try:
        experiment_entry = await get_experiment_entry_by_id_and_user(experiment_id, g.user_id)
        if not experiment_entry:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 404
        
        if not os.path.isdir(os.path.join(PRIVATE_DIRECTORY, experiment_entry['name'])):
            # Result directory doesn't exist
            return jsonify(USER_MESSAGES["EXPERIMENT_RESULT_DIR_NOT_FOUND"]), 404
        
        result_file = os.path.join(PRIVATE_DIRECTORY, experiment_entry['name'], 'results')
        if not os.path.isfile(result_file):
            # Result file doesn't exist
            return jsonify(USER_MESSAGES["EXPERIMENT_RESULT_NOT_FOUND"]), 404
        
        # Erase the lines of result_file
        with open(result_file, 'w') as f:
            f.write('')
            
        return jsonify(USER_MESSAGES["EXPERIMENT_ERASED"]), 200
    
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@experiments_routes.route('/<experiment_id>', methods=['DELETE'])
@require_auth
async def delete_experiment(experiment_id):
    """ 
        This route deletes an experiment based on the experiment ID. 
        It deletes both the DB entry and the associated files of the experiment. 
    """
    try:
        experiment_entry = await get_experiment_entry_by_id_and_user(experiment_id, g.user_id)
        if not experiment_entry:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 404
        
        # Delete all the directories of the experiment
        await delete_experimental_files_and_folders(experiment_entry['name'])
       
        # Delete from DB
        deleted = await delete_experiment_entry(experiment_entry['_id'])
        if not deleted:
            return jsonify(USER_MESSAGES["EXPERIMENT_DELETE_FAILED"]), 500
        
        return jsonify(USER_MESSAGES["EXPERIMENT_DELETED"]), 200
    
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@experiments_routes.route('/download/<experiment_id>', methods=['GET'])
async def download_results(experiment_id):
    """ 
        This route allows the experimenter to download the results of an experiment as a CSV file based on the experiment ID. 
    """
    try:
        exp = await get_experiment_entry_by_id(experiment_id)
        if not exp:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 404
        
        results_dir = os.path.join(PRIVATE_DIRECTORY,exp['name']) # Public directory with experiment as subdirectory
        filename = 'results'
        file_path = os.path.join(results_dir, filename)
        if not os.path.isfile(file_path):
            return jsonify(USER_MESSAGES["EXPERIMENT_RESULT_NOT_FOUND"]), 404
        
        csv_content = processResultFile(file_path)

        # Convert string CSV to bytes for sending
        csv_bytes = csv_content.encode("utf-8")

        return await send_file(
            BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True
        )
        
    except Exception as e:
        print(f"Error downoading the results: {e}")
        return jsonify({"error": str(e)}), 500
    
    
@experiments_routes.route('/download/source/<experiment_id>', methods=['GET'])
async def download_source_zip(experiment_id):
    """ 
        This route allows the experimenter to download the source zip file of an experiment based on the experiment ID. 
    """
    try:
        exp = await get_experiment_entry_by_id(experiment_id)
        if not exp:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 404
        
        source_zip_path = Path(SOURCE_FILE_DIRECTORY) / f"temp_{exp['name']}.zip"

        if not os.path.isfile(source_zip_path):
            return jsonify(USER_MESSAGES["SOURCE_ZIP_NOT_FOUND"]), 404
        
        # Read the zip file as bytes and send
        with open(source_zip_path, "rb") as f:
            zip_bytes = f.read()

        return await send_file(
            BytesIO(zip_bytes),
            mimetype="application/zip",
            as_attachment=True,
            attachment_filename=f"{exp['name']}_source.zip"

        )
        
    except Exception as e:
        print(f"Error downloading the source zip: {e}")
        return jsonify({"error": str(e)}), 500