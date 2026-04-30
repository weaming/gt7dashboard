import copy
import logging
import os
import time
from typing import List

os.environ.setdefault('BOKEH_SIMPLE_WS', 'true')

import bokeh.application
from bokeh.driving import linear
from bokeh.layouts import layout
from bokeh.models import (
    Button,
    CheckboxGroup,
    ColumnDataSource,
    Div,
    Paragraph,
    Select,
    TabPanel,
    Tabs,
)
from bokeh.plotting import curdoc, figure

from gt7dashboard import gt7communication, gt7diagrams, gt7help, gt7helper
from gt7dashboard.gt7diagrams import get_speed_peak_and_valley_diagram, hide_toolbar
from gt7dashboard.gt7help import get_help_div
from gt7dashboard.gt7helper import (
    calculate_time_diff_by_distance,
    get_data_dir,
    list_lap_files_from_path,
    load_laps_from_json,
    save_laps_to_json,
    save_laps_to_path,
)
from gt7dashboard.gt7lap import Lap

# set logging level to debug
logger = logging.getLogger('main.py')
logger.setLevel(logging.DEBUG)

BRAKE_POINT_RENDERER_PREFIX = 'brake-points'
RECONNECT_AFTER_SECONDS = 8
RECONNECT_INTERVAL_SECONDS = 8
FIRST_TELEMETRY_RECONNECT_AFTER_SECONDS = 30
CONNECTION_STATUS_REFRESH_MS = 250
ADDITIONAL_LAP_COLORS = ['blue', 'magenta', 'green', 'orange', 'black', 'purple']


def update_connection_info():
    is_connected = app.gt7comm.is_connected()

    if is_connected:
        connection_info_html = "<p title='已连接' style='color:green; font-size:1.5em; line-height:1;'>●</p>"
    else:
        connection_info_html = "<p title='未连接' style='color:red; font-size:1.5em; line-height:1;'>●</p>"

    if div_connection_info.text != connection_info_html:
        div_connection_info.text = connection_info_html

    return is_connected


def update_connection_status():
    global g_connection_status_stored

    try:
        is_connected = update_connection_info()

        if is_connected != g_connection_status_stored:
            g_connection_status_stored = is_connected
            if not is_connected:
                if app.gt7comm.has_received_data:
                    logger.warning('PS5 connection lost, will attempt reconnection')
                else:
                    logger.info('Waiting for PS5 telemetry')

        if is_connected:
            return

        if app.gt7comm.has_received_data:
            last_data_age = time.time() - app.gt7comm.last_data_received_at
            if last_data_age > RECONNECT_AFTER_SECONDS:
                request_gt7_reconnect('No PS5 data for %.0fs, forcing reconnection' % last_data_age)
            return

        if app.gt7comm.socket_age_seconds > FIRST_TELEMETRY_RECONNECT_AFTER_SECONDS:
            request_gt7_reconnect(
                'No initial PS5 telemetry after %.0fs, restarting socket' % app.gt7comm.socket_age_seconds
            )
    except Exception:
        logger.exception('Error updating connection status')


def update_reference_lap_select(laps):
    reference_lap_select.options = [tuple(('-1', '最佳圈'))] + gt7helper.bokeh_tuple_for_list_of_laps(laps)


@linear()
def update_fuel_map(step):
    global g_stored_fuel_map
    try:
        if len(app.gt7comm.laps) == 0:
            div_fuel_map.text = ''
            return

        last_lap = app.gt7comm.laps[0]

        if last_lap == g_stored_fuel_map:
            return
        else:
            g_stored_fuel_map = last_lap

        # TODO Add real live data during a lap
        div_fuel_map.text = gt7diagrams.get_fuel_map_html_table(last_lap)
    except Exception:
        logger.exception('Error updating fuel map')


def update_race_lines(laps: List[Lap], reference_lap: Lap):
    """
    This function updates the race lines on the second tab with the amount of laps
    that the race line tab can hold
    """
    global race_lines, race_lines_data

    reference_lap_data = reference_lap.get_data_dict()

    for i, lap in enumerate(laps[: len(race_lines)]):
        logger.info(f'Updating Race Line for Lap {len(laps) - i} - {lap.title} and reference lap {reference_lap.title}')

        race_lines[i].title.text = '圈 %d - %s (%s)，参考圈: %s (%s)' % (
            len(laps) - i,
            lap.title,
            lap.car_name(),
            reference_lap.title,
            reference_lap.car_name(),
        )

        lap_data = lap.get_data_dict()
        race_lines_data[i][0].data_source.data = lap_data
        race_lines_data[i][1].data_source.data = lap_data
        race_lines_data[i][2].data_source.data = lap_data

        race_lines_data[i][3].data_source.data = reference_lap_data
        race_lines_data[i][4].data_source.data = reference_lap_data
        race_lines_data[i][5].data_source.data = reference_lap_data

        race_lines[i].axis.visible = False

        gt7diagrams.add_annotations_to_race_line(race_lines[i], lap, reference_lap)

        # Fixme not working
        race_lines[i].x_range = race_lines[0].x_range


def update_header_line(div: Div, last_lap: Lap, reference_lap: Lap):
    div.text = (
        f'<p><b>上一圈: {last_lap.title} ({last_lap.car_name()})<b></p>'
        f'<p><b>参考圈: {reference_lap.title} ({reference_lap.car_name()})<b></p>'
    )


def update_lap_change():
    """
    Is called whenever a lap changes.
    It detects if the telemetry date retrieved is the same as the data displayed.
    If true, it updates all the visual elements.
    """
    global g_laps_stored
    global g_session_stored
    global g_telemetry_update_needed
    global g_reference_lap_selected

    try:
        _do_update_lap_change()
    except Exception:
        logger.exception('Error updating lap change, skipping this cycle')

    g_laps_stored = app.gt7comm.get_laps().copy()
    g_telemetry_update_needed = False


def _clear_all_visuals():
    """Clear all chart data sources and divs when laps are cleared."""
    global race_lines, race_lines_data, race_time_table, corner_analysis

    empty_dict = Lap().get_data_dict()
    empty_time_diff = {'distance': [], 'timedelta': []}
    empty_race_line = {'raceline_x': [], 'raceline_z': []}

    race_diagram.source_last_lap.data = empty_dict
    race_diagram.source_reference_lap.data = empty_dict
    race_diagram.source_median_lap.data = empty_dict
    race_diagram.source_time_diff.data = empty_time_diff

    last_lap_race_line.data_source.data = empty_race_line
    reference_lap_race_line.data_source.data = empty_race_line

    for line_data in race_lines_data:
        for source in line_data:
            source.data_source.data = empty_dict

    clear_break_points(s_race_line)

    race_time_table.show_laps([])
    corner_analysis.update([])

    div_header_line.text = ''
    div_speed_peak_valley_diagram.text = ''
    div_fuel_map.text = ''
    div_deviance_laps_on_display.text = ''


def _do_update_lap_change():
    global g_session_stored
    global g_reference_lap_selected
    global g_laps_stored
    global g_telemetry_update_needed

    update_start_time = time.time()

    laps = app.gt7comm.get_laps()

    if app.gt7comm.session != g_session_stored:
        update_tuning_info()
        g_session_stored = copy.copy(app.gt7comm.session)

    # This saves on cpu time, 99.9% of the time this is true
    if laps == g_laps_stored and not g_telemetry_update_needed:
        return

    if len(laps) == 0:
        _clear_all_visuals()
        g_laps_stored = laps
        g_telemetry_update_needed = False
        return

    logger.debug('Rerendering laps')

    reference_lap = Lap()

    if len(laps) > 0:
        last_lap = laps[0]

        if len(laps) > 1:
            reference_lap = gt7helper.get_last_reference_median_lap(
                laps, reference_lap_selected=g_reference_lap_selected
            )[1]

            try:
                div_speed_peak_valley_diagram.text = get_speed_peak_and_valley_diagram(last_lap, reference_lap)
            except Exception:
                logger.exception('Error updating speed peak and valley diagram')

        update_header_line(div_header_line, last_lap, reference_lap)

    logger.debug('Updating of %d laps' % len(laps))

    start_time = time.time()
    try:
        update_time_table(laps)
    except Exception:
        logger.exception('Error updating time table')
    logger.debug('Updating time table took %dms' % ((time.time() - start_time) * 1000))

    start_time = time.time()
    try:
        update_reference_lap_select(laps)
    except Exception:
        logger.exception('Error updating reference lap select')
    logger.debug('Updating reference lap select took %dms' % ((time.time() - start_time) * 1000))

    start_time = time.time()
    try:
        update_speed_velocity_graph(laps)
    except Exception:
        logger.exception('Error updating speed velocity graph')
    logger.debug('Updating speed velocity graph took %dms' % ((time.time() - start_time) * 1000))

    start_time = time.time()
    try:
        update_race_lines(laps, reference_lap)
    except Exception:
        logger.exception('Error updating race lines')
    logger.debug('Updating race lines took %dms' % ((time.time() - start_time) * 1000))

    start_time = time.time()
    try:
        corner_analysis.update(laps)
    except Exception:
        logger.exception('Error updating corner analysis')
    logger.debug('Updating corner analysis took %dms' % ((time.time() - start_time) * 1000))

    logger.debug('End of updating laps, whole Update took %dms' % ((time.time() - update_start_time) * 1000))


def update_speed_velocity_graph(laps: List[Lap]):
    last_lap, reference_lap, median_lap = gt7helper.get_last_reference_median_lap(
        laps, reference_lap_selected=g_reference_lap_selected
    )

    if last_lap:
        last_lap_data = last_lap.get_data_dict()
        race_diagram.source_last_lap.data = last_lap_data
        last_lap_race_line.data_source.data = last_lap_data

        if reference_lap and len(reference_lap.data_speed) > 0:
            reference_lap_data = reference_lap.get_data_dict()
            race_diagram.source_time_diff.data = calculate_time_diff_by_distance(reference_lap, last_lap)
            race_diagram.source_reference_lap.data = reference_lap_data
            reference_lap_race_line.data_source.data = reference_lap_data

    if median_lap:
        race_diagram.source_median_lap.data = median_lap.get_data_dict()

    s_race_line.legend.visible = False
    s_race_line.axis.visible = False

    fastest_laps = race_diagram.update_fastest_laps_variance(laps)
    logger.info('Updating Speed Deviance with %d fastest laps' % len(fastest_laps))
    div_deviance_laps_on_display.text = ''
    for fastest_lap in fastest_laps:
        div_deviance_laps_on_display.text += f'<b>圈 {fastest_lap.number}:</b> {fastest_lap.title}<br>'

    # Update breakpoints
    # Adding Brake Points is slow when rendering, this is on Bokehs side about 3s
    brake_points_enabled = os.environ.get('GT7_ADD_BRAKEPOINTS') == 'true'

    if not brake_points_enabled:
        clear_break_points(s_race_line)
        return

    update_break_points(last_lap, s_race_line, 'blue')
    update_break_points(reference_lap, s_race_line, 'magenta')


def update_break_points(lap: Lap, race_line: figure, color: str):
    source_data = {'x': [], 'y': []}
    if lap and len(lap.data_braking) > 0:
        brake_points_x, brake_points_y = gt7helper.get_brake_points(lap)
        source_data = {'x': brake_points_x, 'y': brake_points_y}

    renderer_name = f'{BRAKE_POINT_RENDERER_PREFIX}-{color}'
    for renderer in race_line.renderers:
        if renderer.name == renderer_name and hasattr(renderer, 'data_source'):
            renderer.data_source.data = source_data
            return

    race_line.scatter(
        x='x',
        y='y',
        marker='circle',
        size=10,
        fill_color=color,
        line_color=color,
        name=renderer_name,
        source=ColumnDataSource(data=source_data),
    )


def clear_break_points(race_line: figure):
    for renderer in race_line.renderers:
        if renderer.name and renderer.name.startswith(BRAKE_POINT_RENDERER_PREFIX):
            renderer.data_source.data = {'x': [], 'y': []}


def update_time_table(laps: List[Lap]):
    global race_time_table
    global lap_times_source
    # FIXME time table is not updating
    logger.info('Adding %d laps to table' % len(laps))
    race_time_table.show_laps(laps)

    # t_lap_times.trigger("source", t_lap_times.source, t_lap_times.source)


def reset_button_handler(event):
    global g_telemetry_update_needed
    logger.info('reset button clicked')
    race_diagram.delete_all_additional_laps()

    app.gt7comm.load_laps([], replace_other_laps=True)
    app.gt7comm.reset()
    g_telemetry_update_needed = True


def delete_selected_laps_handler(event):
    global g_reference_lap_selected
    global g_telemetry_update_needed

    selected_indices = sorted(set(race_time_table.lap_times_source.selected.indices), reverse=True)
    if len(selected_indices) == 0:
        return

    removed_laps = app.gt7comm.delete_laps_by_indices(selected_indices)
    if len(removed_laps) == 0:
        return

    logger.info('Deleted %d selected laps', len(removed_laps))

    if g_reference_lap_selected in removed_laps:
        g_reference_lap_selected = None
        reference_lap_select.value = '-1'

    race_time_table.lap_times_source.selected.indices = []
    race_diagram.delete_all_additional_laps()
    g_telemetry_update_needed = True
    update_lap_change()


def always_record_checkbox_handler(event, old, new):
    if len(new) == 2:
        logger.info('Set always record data to True')
        app.gt7comm.always_record_data = True
    else:
        logger.info('Set always record data to False')
        app.gt7comm.always_record_data = False


def log_lap_button_handler(event):
    app.gt7comm.finish_lap(manual=True)
    logger.info('Added a lap manually to the list of laps: %s' % app.gt7comm.laps[0])


def save_button_handler(event):
    if len(app.gt7comm.laps) > 0:
        path = save_laps_to_json(app.gt7comm.laps)
        logger.info('Saved %d laps as %s' % (len(app.gt7comm.laps), path))


def load_laps_handler(attr, old, new):
    logger.info('Loading %s' % new)
    race_diagram.delete_all_additional_laps()
    app.gt7comm.load_laps(load_laps_from_json(new), replace_other_laps=True)


def load_button_handler(event):
    load_laps_handler(None, None, select.value)


def load_reference_lap_handler(attr, old, new):
    global g_reference_lap_selected
    global reference_lap_select
    global g_telemetry_update_needed

    if int(new) == -1:
        # Set no reference lap
        g_reference_lap_selected = None
    else:
        g_reference_lap_selected = g_laps_stored[int(new)]
        logger.info('Loading %s as reference' % g_laps_stored[int(new)].format())

    g_telemetry_update_needed = True
    update_lap_change()


def update_tuning_info():
    div_tuning_info.text = """<h4>调校信息</h4>
    <p>最高速度: <b>%d</b> kph</p>
    <p>最小车身高度: <b>%d</b> mm</p>""" % (
        app.gt7comm.session.max_speed,
        app.gt7comm.session.min_body_height,
    )


def get_race_lines_layout(number_of_race_lines):
    """
    This function returns the race lines layout.
    It returns a grid of 3x3 race lines. Red is braking.
    Green is throttling.
    """
    i = 0
    race_line_diagrams = []
    race_lines_data = []

    sizing_mode = 'scale_height'

    while i < number_of_race_lines:
        (
            s_race_line,
            throttle_line,
            breaking_line,
            coasting_line,
            reference_throttle_line,
            reference_breaking_line,
            reference_coasting_line,
        ) = gt7diagrams.get_throttle_braking_race_line_diagram()
        s_race_line.sizing_mode = sizing_mode
        race_line_diagrams.append(s_race_line)
        race_lines_data.append(
            [
                throttle_line,
                breaking_line,
                coasting_line,
                reference_throttle_line,
                reference_breaking_line,
                reference_coasting_line,
            ]
        )
        i += 1

    l = layout(children=race_line_diagrams)
    l.sizing_mode = sizing_mode

    return l, race_line_diagrams, race_lines_data


app = bokeh.application.Application


def request_gt7_reconnect(reason: str):
    now = time.time()
    last_restart_time = getattr(app, 'last_gt7_restart_time', 0)
    if now - last_restart_time < RECONNECT_INTERVAL_SECONDS:
        return

    logger.warning(reason)
    app.gt7comm.restart()
    app.last_gt7_restart_time = now


# Share the gt7comm connection between sessions by storing them as an application attribute
if not hasattr(app, 'gt7comm'):
    playstation_ip = os.environ.get('GT7_PLAYSTATION_IP')
    load_laps_path = os.environ.get('GT7_LOAD_LAPS_PATH')

    if not playstation_ip:
        playstation_ip = '255.255.255.255'
        logger.info(f'No IP set in env var GT7_PLAYSTATION_IP using broadcast at {playstation_ip}')

    app.gt7comm = gt7communication.GT7Communication(playstation_ip)

    if load_laps_path:
        app.gt7comm.load_laps(load_laps_from_json(load_laps_path), replace_other_laps=True)

    app.gt7comm.start()

    # Auto-save all laps on each completed lap
    def on_lap_completed(_completed_lap):
        try:
            laps = app.gt7comm.laps
            if len(laps) > 0:
                save_laps_to_path(laps, os.path.join(get_data_dir(), 'auto_save.json'))
                logger.debug('Auto-saved %d laps' % len(laps))
        except Exception:
            logger.exception('Error in lap auto-save')

    app.gt7comm.set_lap_callback(on_lap_completed)
else:
    # Reuse existing thread
    if not app.gt7comm.is_connected():
        if app.gt7comm.has_received_data:
            request_gt7_reconnect('Restarting gt7communication because of no connection')
        else:
            logger.info('Waiting for PS5 telemetry')
    else:
        # Existing thread has connection, proceed
        pass


# def init_lap_times_source():
#     global lap_times_source
#     lap_times_source.data = gt7helper.pd_data_frame_from_lap([], best_lap_time=app.gt7comm.session.last_lap)
#
# init_lap_times_source()

g_laps_stored = []
g_session_stored = None
g_connection_status_stored = None
g_reference_lap_selected = None
g_stored_fuel_map = None
g_telemetry_update_needed = False

stored_lap_files = gt7helper.bokeh_tuple_for_list_of_lapfiles(
    list_lap_files_from_path(os.path.join(os.getcwd(), get_data_dir()))
)

race_diagram = gt7diagrams.RaceDiagram(width=1000)
race_time_table = gt7diagrams.RaceTimeTable()
corner_analysis = gt7diagrams.CornerAnalysis(width=1000)


def table_row_selection_callback(attrname, old, new):
    global g_laps_stored
    global race_diagram
    global race_time_table

    selection_index = race_time_table.lap_times_source.selected.indices
    logger.info('you have selected the row nr ' + str(selection_index))

    # Update delete button label with selected lap numbers
    if selection_index:
        lap_numbers = [g_laps_stored[i].number for i in selection_index if i < len(g_laps_stored)]
        delete_selected_laps_button.label = '删除选中圈 (#' + ', #'.join(str(n) for n in lap_numbers) + ')'
    else:
        delete_selected_laps_button.label = '删除选中圈'

    color_index = len(race_diagram.sources_additional_laps)

    for index in selection_index:
        if index >= len(g_laps_stored):
            continue

        lap_to_add = g_laps_stored[index]
        if race_diagram.has_additional_lap(lap_to_add):
            continue

        color = ADDITIONAL_LAP_COLORS[color_index % len(ADDITIONAL_LAP_COLORS)]
        color_index += 1
        race_diagram.add_additional_lap_to_race_diagram(color, lap_to_add, visible=True)


race_time_table.lap_times_source.selected.on_change('indices', table_row_selection_callback)

# Race line

race_line_tooltips = [('index', '$index'), ('Breakpoint', '')]
race_line_width = 250
speed_diagram_width = 1200
total_width = race_line_width + speed_diagram_width
s_race_line = figure(
    title='赛车线',
    x_axis_label='x',
    y_axis_label='z',
    match_aspect=True,
    width=race_line_width,
    height=race_line_width,
    active_drag='box_zoom',
    tooltips=race_line_tooltips,
)

# We set this to true, since maps appear flipped in the game
# compared to their actual coordinates
s_race_line.y_range.flipped = True

hide_toolbar(s_race_line)

last_lap_race_line = s_race_line.line(
    x='raceline_x',
    y='raceline_z',
    legend_label='上一圈',
    line_width=1,
    color='blue',
    source=ColumnDataSource(data={'raceline_x': [], 'raceline_z': []}),
)
reference_lap_race_line = s_race_line.line(
    x='raceline_x',
    y='raceline_z',
    legend_label='参考圈',
    line_width=1,
    color='magenta',
    source=ColumnDataSource(data={'raceline_x': [], 'raceline_z': []}),
)

select_title = Paragraph(text='', align='center')
select = Select(value='laps', options=stored_lap_files)
load_button = Button(label='加载')
load_button.on_click(load_button_handler)

reference_lap_select = Select(value='laps')
reference_lap_select.on_change('value', load_reference_lap_handler)

manual_log_button = Button(label='立即记录')
manual_log_button.on_click(log_lap_button_handler)

save_button = Button(label='保存所有')
save_button.on_click(save_button_handler)

reset_button = Button(label='清空')
reset_button.on_click(reset_button_handler)

delete_selected_laps_button = Button(label='删除选中圈')
delete_selected_laps_button.on_click(delete_selected_laps_handler)

div_tuning_info = Div(width=200, height=100)

# div_last_lap = Div(width=200, height=125)
# div_reference_lap = Div(width=200, height=125)
div_speed_peak_valley_diagram = Div(width=200, height=125)
div_gt7_dashboard = Div(width=120, height=30)
div_header_line = Div(width=400, height=30)
div_connection_info = Div(width=30, height=30)
div_deviance_laps_on_display = Div(width=200, height=race_diagram.f_speed_variance.height)

div_fuel_map = Div(width=200, height=125, css_classes=['fuel_map'])

div_gt7_dashboard.text = "<a href='https://github.com/weaming/gt7dashboard' target='_blank'>GT7 Dashboard</a>"
update_connection_info()

LABELS = ['记录回放']

checkbox_group = CheckboxGroup(labels=LABELS, active=[1])
checkbox_group.on_change('active', always_record_checkbox_handler)

race_time_table.t_lap_times.width = 970

l1 = layout(
    children=[
        [
            get_help_div(gt7help.HEADER),
            div_connection_info,
            div_gt7_dashboard,
            div_header_line,
            reset_button,
            delete_selected_laps_button,
            save_button,
            select_title,
            select,
            load_button,
            get_help_div(gt7help.LAP_CONTROLS),
        ],
        [
            get_help_div(gt7help.TIME_DIFF),
            race_diagram.f_time_diff,
            layout(children=[manual_log_button, checkbox_group, reference_lap_select]),
            get_help_div(gt7help.MANUAL_CONTROLS),
        ],
        [get_help_div(gt7help.SPEED_DIAGRAM), race_diagram.f_speed, s_race_line, get_help_div(gt7help.RACE_LINE_MINI)],
        [
            get_help_div(gt7help.SPEED_VARIANCE),
            race_diagram.f_speed_variance,
            div_deviance_laps_on_display,
            get_help_div(gt7help.SPEED_VARIANCE),
        ],
        [
            get_help_div(gt7help.THROTTLE_DIAGRAM),
            race_diagram.f_throttle,
            div_speed_peak_valley_diagram,
            get_help_div(gt7help.SPEED_PEAKS_AND_VALLEYS),
        ],
        [get_help_div(gt7help.YAW_RATE_DIAGRAM), race_diagram.f_yaw_rate],
        [get_help_div(gt7help.BRAKING_DIAGRAM), race_diagram.f_braking],
        [get_help_div(gt7help.COASTING_DIAGRAM), race_diagram.f_coasting],
        [get_help_div(gt7help.GEAR_DIAGRAM), race_diagram.f_gear],
        [get_help_div(gt7help.RPM_DIAGRAM), race_diagram.f_rpm],
        [get_help_div(gt7help.BOOST_DIAGRAM), race_diagram.f_boost],
        [get_help_div(gt7help.TIRE_DIAGRAM), race_diagram.f_tires],
        [
            get_help_div(gt7help.TIME_TABLE),
            race_time_table.t_lap_times,
            get_help_div(gt7help.FUEL_MAP),
            div_fuel_map,
            get_help_div(gt7help.TUNING_INFO),
            div_tuning_info,
        ],
    ]
)


l2, race_lines, race_lines_data = get_race_lines_layout(number_of_race_lines=1)

l3 = layout(
    [
        [reset_button, save_button],
        [
            div_speed_peak_valley_diagram,
            div_fuel_map,
        ],  # TODO Race table does not render twice, one rendering will be empty
    ],
    sizing_mode='stretch_width',
)

#  Setup the tabs
tab1 = TabPanel(child=l1, title='提升圈速')
tab2 = TabPanel(child=l2, title='赛车线')
tab3 = TabPanel(child=l3, title='比赛')
tab4 = TabPanel(child=corner_analysis.layout, title='弯道分析')
tabs = Tabs(tabs=[tab1, tab2, tab3, tab4])

curdoc().add_root(tabs)
curdoc().title = 'GT7 Dashboard'

curdoc().add_periodic_callback(update_connection_status, CONNECTION_STATUS_REFRESH_MS)
# This will only trigger once per lap, but we check every second if anything happened
curdoc().add_periodic_callback(update_lap_change, 1000)
curdoc().add_periodic_callback(update_fuel_map, 5000)
