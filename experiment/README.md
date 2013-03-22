# Mass Inference Experiment

## Structure

* `config` -- trial metadata and order for each condition
* `config/hits` -- Mechanical Turk HITs
* `data` -- auto-generated folder with participant data
* `db_tools.py` -- helper functions for interacting with the databases
* `gen_conditions.py` -- script for generating experimental conditions
* `index.py` -- server-side experiment code
* `logs` -- auto-generated folder with experiment logs
* `resources` -- static or client-side resources
* `resources/css/experiment.css` -- all CSS formatting
* `resources/flowplayer` -- video player, see [http://flowplayer.org/](http://flowplayer.org/)
* `resources/html/experiment.html` -- HTML template code
* `resources/images` -- non-stimuli images
* `resources/js/experiment.js` -- experiment JavaScript

## Setup

To run the experiment, you'll need to do a few thingsf first.

1. **Create a symlink to `stimuli`.** This requires access to the mass
learning stimuli submodule (`git submodule init stimuli`, `git
submodule update stimuli`). Then:

   ```ln -s ../stimuli/www stimuli```

2. **Initialize the database.** The database stores IP addresses,
validation codes, completion codes, conditions, and participant
ids. It is not included in the repository for privacy reasons and
should never be committed; you will need to manually initialize it. To
do this:

   ```
   $ python -i db_tools.py  
   create()  
   Backing up old database to 'data/data.db.bak'...  
   Creating new database 'data/data.db'...  
   Created 'Participants' table
   ```

3. **Make `index.py` executable.** The following command should do it:

   ```chmod +x index.py```

## Access

To access the experiment, you'll need to set up a webserver and place
the repository somewhere that the server has access. Navigate your web
browser to `http://path/to/experiment/index.py?cond=<condition>`,
where `<condition>` refers to the code for the experimental condition,
such as `E-fb-10-cb0`.
