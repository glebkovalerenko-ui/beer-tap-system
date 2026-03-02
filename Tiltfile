docker_compose('docker-compose.tilt.yml')

docker_build(
  'beer_backend_api',   # совпадает с image: beer_backend_api
  'backend',            # build context
  live_update=[
    sync('backend', '/app'),
    restart_container(),
  ],
)

dc_resource('beer_backend_api')
dc_resource('postgres')