    
from quart import Blueprint
from quart import Quart, Response, request, send_from_directory, jsonify,abort
from messages import USER_MESSAGES
import server_conf  # Import your configuration file
from datetime import datetime
import os
import json
from utils import getExperimentFromHeaders, extractMediaFilePath, getExperimentNameFromPath
from experiments import get_experiment_entry_by_name

PORT = server_conf.PORT
PRIVATE_DIRECTORY = server_conf.PRIVATE_DIRECTORY
PUBLIC_DIRECTORY = server_conf.PUBLIC_DIRECTORY
BASE_APPLICATION_URL = server_conf.BASE_APPLICATION_URL
PWD = os.getcwd()  # Define PWD dynamically or from config
IBEX_WORKING_DIR = os.path.abspath(server_conf.IBEX_WORKING_DIR)
CHUNK_DIR = os.path.join(PUBLIC_DIRECTORY, server_conf.CHUNK_INCLUDES_DIR)

pcibex_routes = Blueprint('pcibex', __name__)

@pcibex_routes.route('/<path:path>', methods=['GET'])
async def send_files(path): 
    """ 
        This route serves static files required for the experiment. 
        'setsquare' logic is directly implemented based on the original documentation. 
        'allchunks' logic is extended based on their original implementation. It pulls the CSV and HTML necessary to load the experiment. 
        However, the same route is also necessary to serve media files necessary for the experiment, 
        and such requests do not contain any query params. So a separate if-else block takes care of such requests.
    """
    if 'setsquare' in request.args:
        setsquare = request.args.get("setsquare", None)
        experiment_name = getExperimentNameFromPath(path)
        if experiment_name is None:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 400
        counter_file = os.path.join(PRIVATE_DIRECTORY,experiment_name, "counter")
        
        if setsquare is not None:
          if setsquare.lower().startswith("inc-"):
            previous_value = int(open(counter_file,"r").read()) if os.path.exists(counter_file) else 0
            setsquare = int(previous_value) + int(setsquare.lower().lstrip("inc-"))
          with open(counter_file,"w") as counter:
            counter.write(str(int(setsquare)))
          return jsonify("success"), 200
        else:
          return jsonify("error"), 400
    
    if 'allchunks' in request.args:
        experiment_name = getExperimentNameFromPath(path)
        if experiment_name is None:
            return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 400
        jsondict = {}
        chunk_folder = os.path.join(CHUNK_DIR, experiment_name)
        if not os.path.isdir(chunk_folder):
            # Experiments without chunk_includes content have nothing to return.
            return jsonify(jsondict)
        try:
           for fname in os.listdir(chunk_folder):
                file_path = os.path.join(chunk_folder, fname)

                if fname.endswith((".wav", ".mp3", ".m4a", ".jpeg", ".jpg", ".png")) or os.path.isdir(file_path):
                    continue  # Skip audio files and directories

                try: 
                    with open(file_path, 'r', encoding='utf-8') as f:
                        jsondict[fname] = f.read()
                except IOError as e:
                    print(e)
                    if e.errno:
                        continue  # Skip directories
                    return "500 Internal Server Error", 500

        except Exception as e:
            return f"Error: {str(e)}", 500

        return jsonify(jsondict)
    
    if path.endswith((".wav", ".mp3", ".m4a", ".jpeg", ".jpg", ".png")):
      # Media file, so extract the path
      media_file_path = extractMediaFilePath(path)
      if media_file_path is None:
        abort(404)
      return await send_from_directory(os.path.join(CHUNK_DIR, media_file_path[0]), media_file_path[1])
    return await send_from_directory(PUBLIC_DIRECTORY, path)
  
@pcibex_routes.route('/send', methods=['GET','POST','OPTIONS'])
async def server():
    """ 
      This route receieves the results of the experiment from the client (experiment participant in our case), 
      and saves the results as a file.
    """
    data = (await request.data).decode("utf-8")
    experiment_name = getExperimentFromHeaders(request.headers.get('Referer'))
    if experiment_name is None:
        return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 400
    experiment_entry = await get_experiment_entry_by_name(experiment_name)
    if not experiment_entry:
        return jsonify(USER_MESSAGES["EXPERIMENT_NOT_FOUND"]), 404
    data_json = json.loads(data)
    if data_json[0] is False:
      counter_value = 0
      counter_file = os.path.join(PRIVATE_DIRECTORY,experiment_name, "counter")
      if os.path.exists(counter_file):
        counter_from_file = open(counter_file,"r").read()
        counter_value = int(counter_from_file) if counter_from_file.isdigit() else counter_value
      open(counter_file,"w").write(str(counter_value+1))
    result_file = os.path.join(PRIVATE_DIRECTORY,experiment_name,"results")
    open_mode = "a" if os.path.exists(result_file) else "w"
    open(result_file,open_mode).write(f"{data}\n")

    return {'url': experiment_entry['redirect_url']}

@pcibex_routes.route('/counter', methods=['GET'])
async def counter():
    """ 
        This route serves the current value of the counter for a given experiment. 
        However, it is strongly discouraged to use this counter value since a new counter value is generated for every page refresh. 
        This is, however, necessary for loading the experiment as per PCIbex design, and hence implemented here.
    """
    experiment_name = request.args.get("exp", None)
    if not experiment_name:
      return "Error"
    else:
      counter_file = os.path.join(PRIVATE_DIRECTORY,experiment_name, "counter")
      if not os.path.exists(counter_file):
          open(counter_file,"w").write("0")
      return Response(f"window.__counter_value_from_server__ = {open(counter_file,'r').read()};", mimetype="text/javascript")
    

    