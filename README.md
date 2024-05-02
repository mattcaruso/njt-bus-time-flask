# NJ Transit Bus Times Flask API
This project utilizes Flask to create a minimal HTTP API, connected to a Postgres database, which serves NJ Transit's
bus scheduled GTFS data. It's based on the [minimal-flask-api repo](https://github.com/markdouthwaite/minimal-flask-api) 
and [blog post](https://towardsdatascience.com/flask-in-production-minimal-web-apis-2e0859736df) by Mark Douthwaite 
which lays out helpful guidelines to host Flask in a production environment.

## Why is this service necessary?


# Components
## minimal-flask-api
This [template repository](https://docs.github.com/en/github/creating-cloning-and-archiving-repositories/creating-a-repository-from-a-template)
 was used as a starting point because it contains a number of architectural decisions already made and great 
recommendations for dockerized hosting.

The template has been set up for use with Python >= 3.7 and [Docker](https://www.docker.com/). 

## axilla
Tidbyt's SDK for designing applets is called Pixlet. btjones has created an excellent Netlify
template dubbed [axilla](https://github.com/btjones/axilla) to run Pixlet and render images via HTTP API. You'll 
need to stand up your own axilla server or find another way to render the Starlark script via Pixlet into a base64
image.

## NJ Transit GTFS Data
NJ Transit only provides bus data as a GTFS archive. They provide no official HTTP API. To make up for this, I've 
leveraged [gtfs-db](https://github.com/OpenTransitTools/gtfsdb), which ingests the GTFS zip file and loads it into a
Postgres database. You'll need to follow the instructions in their README to get yourself set up with a database.

# Environment
**Note**: These variables must be set in your local environment before any tests will pass.

| Key               | Example Value                   | Notes                                                                                                                                                                                              |
|-------------------|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TIDBYT_DEVICE_IDS | monkey-banana-231,seal-fish-456 | The Tidbyt device IDs, as found in your Tidbyt app. To push to multiple Tidbyts, use a comma separated list format, as shown. A single string without commas will work for a single target device. |
| TIDBYT_API_KEYS   | ey9178fhalkdgh...,x187dhgladkgh | Your Tidbyt API key, found in the app. You'll have a different API key for each Tidbyt. **Note:** You need to put the order of the API keys in the same order you used for the device IDs!         |
| PGDATABASE        | datbasename                     | Your database credentials where you host NJ Transit GTFS data.                                                                                                                                     |
| PGHOST            | monorail.proxy.rlwy.net         |                                                                                                                                                                                                    |
| PGPASSWORD        | password1234                    |                                                                                                                                                                                                    |
| PGPORT            | 5432                            |                                                                                                                                                                                                    |
| PGUSER            | postgres                        |                                                                                                                                                                                                    |

