from typing import List

import bokeh
from bokeh.layouts import layout
from bokeh.models import ColumnDataSource, Label, Column, TableColumn, DataTable, Range1d, Div
from bokeh.transform import dodge
from bokeh.plotting import figure

from gt7dashboard import gt7helper
from gt7dashboard.gt7lap import Lap


def hide_toolbar(target_figure: figure):
    target_figure.toolbar.visible = False


def get_throttle_braking_race_line_diagram():
    # TODO Make this work, tooltips just show breakpoint
    race_line_tooltips = [('index', '$index')]
    s_race_line = figure(
        title='赛车线',
        match_aspect=True,
        active_scroll='wheel_zoom',
        tooltips=race_line_tooltips,
    )

    # We set this to true, since maps appear flipped in the game
    # compared to their actual coordinates
    s_race_line.y_range.flipped = True

    hide_toolbar(s_race_line)

    s_race_line.axis.visible = False
    s_race_line.xgrid.visible = False
    s_race_line.ygrid.visible = False

    throttle_line = s_race_line.line(
        x='raceline_x_throttle',
        y='raceline_z_throttle',
        legend_label='上一圈油门',
        line_width=5,
        color='green',
        source=ColumnDataSource(data={'raceline_z_throttle': [], 'raceline_x_throttle': []}),
    )
    breaking_line = s_race_line.line(
        x='raceline_x_braking',
        y='raceline_z_braking',
        legend_label='上一圈刹车',
        line_width=5,
        color='red',
        source=ColumnDataSource(data={'raceline_z_braking': [], 'raceline_x_braking': []}),
    )

    coasting_line = s_race_line.line(
        x='raceline_x_coasting',
        y='raceline_z_coasting',
        legend_label='上一圈滑行',
        line_width=5,
        color='blue',
        source=ColumnDataSource(data={'raceline_z_coasting': [], 'raceline_x_coasting': []}),
    )

    # Reference Lap

    reference_throttle_line = s_race_line.line(
        x='raceline_x_throttle',
        y='raceline_z_throttle',
        legend_label='参考圈油门',
        line_width=15,
        alpha=0.3,
        color='green',
        source=ColumnDataSource(data={'raceline_z_throttle': [], 'raceline_x_throttle': []}),
    )
    reference_breaking_line = s_race_line.line(
        x='raceline_x_braking',
        y='raceline_z_braking',
        legend_label='参考圈刹车',
        line_width=15,
        alpha=0.3,
        color='red',
        source=ColumnDataSource(data={'raceline_z_braking': [], 'raceline_x_braking': []}),
    )

    reference_coasting_line = s_race_line.line(
        x='raceline_x_coasting',
        y='raceline_z_coasting',
        legend_label='参考圈滑行',
        line_width=15,
        alpha=0.3,
        color='blue',
        source=ColumnDataSource(data={'raceline_z_coasting': [], 'raceline_x_coasting': []}),
    )

    s_race_line.legend.visible = True

    s_race_line.add_layout(s_race_line.legend[0], 'right')

    s_race_line.legend.click_policy = 'hide'

    return (
        s_race_line,
        throttle_line,
        breaking_line,
        coasting_line,
        reference_throttle_line,
        reference_breaking_line,
        reference_coasting_line,
    )


class RaceTimeTable(object):
    def __init__(self):

        self.columns = [
            TableColumn(field='number', title='#', width=40),
            TableColumn(field='time', title='时间', width=90),
            TableColumn(field='diff', title='差值', width=85),
            TableColumn(field='timestamp', title='时间戳', width=155),
            TableColumn(field='info', title='信息', width=55),
            TableColumn(field='fuelconsumed', title='燃油消耗', width=75),
            TableColumn(field='fullthrottle', title='全油门', width=65),
            TableColumn(field='fullbreak', title='全刹车', width=60),
            TableColumn(field='nothrottle', title='滑行', width=50),
            TableColumn(field='tyrespinning', title='轮胎打滑', width=70),
            TableColumn(field='car_name', title='赛车', width=250),
        ]

        self.lap_times_source = ColumnDataSource(gt7helper.pd_data_frame_from_lap([], best_lap_time=0))
        self.t_lap_times: DataTable

        self.t_lap_times = DataTable(
            source=self.lap_times_source, columns=self.columns, index_position=None, css_classes=['lap_times_table'],
            resizable=True,
        )
        # This will lead to not being rendered
        # self.t_lap_times.autosize_mode = "fit_columns"
        # Maybe this is related: https://github.com/bokeh/bokeh/issues/10512 ?

    def show_laps(self, laps: List[Lap]):
        best_lap = gt7helper.get_best_lap(laps)
        if best_lap == None:
            return

        new_df = gt7helper.pd_data_frame_from_lap(laps, best_lap_time=best_lap.lap_finish_time)
        self.lap_times_source.data = ColumnDataSource.from_df(new_df)


class RaceDiagram(object):
    def __init__(self, width=400):
        """
        Returns figures for time-diff, speed, throttling, braking and coasting.
        All with lines for last lap, best lap and median lap.
        The last return value is the sources object, that has to be altered
        to display data.
        """

        self.speed_lines = []
        self.braking_lines = []
        self.coasting_lines = []
        self.throttle_lines = []
        self.tires_lines = []
        self.rpm_lines = []
        self.gears_lines = []
        self.boost_lines = []
        self.yaw_rate_lines = []

        # Data Sources
        self.source_time_diff = None
        self.source_speed_variance = None
        self.source_last_lap = None
        self.source_reference_lap = None
        self.source_median_lap = None
        self.sources_additional_laps = []

        self.additional_laps: List[Lap] = []

        # This is the number of default laps,
        # last lap, best lap and median lap
        self.number_of_default_laps = 3

        tooltips = [
            ('index', '$index'),
            ('value', '$y'),
            ('速度', '@speed{0}'),
            ('横摆角速度', '@yaw_rate{0.00}'),
            ('油门', '@throttle%'),
            ('刹车', '@brake%'),
            ('滑行', '@coast%'),
            ('档位', '@gear'),
            ('转速', '@rpm{0} RPM'),
            ('距离', '@distance{0} m'),
            ('增压', '@boost{0.00} x 100 kPa'),
        ]

        tooltips_timedelta = [
            ('index', '$index'),
            ('时间差', '@timedelta{0} ms'),
            ('参考值', '@reference{0} ms'),
            ('对比值', '@comparison{0} ms'),
        ]

        self.tooltips_speed_variance = [
            ('index', '$index'),
            ('距离', '@distance{0} m'),
            ('速度偏差', '@speed_variance{0}'),
        ]

        self.f_speed = figure(
            title='上一圈、参考圈、中位圈',
            y_axis_label='速度',
            width=width,
            height=250,
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_speed_variance = figure(
            y_axis_label='速度偏差',
            x_range=self.f_speed.x_range,
            y_range=Range1d(0, 50),
            width=width,
            height=int(self.f_speed.height / 4),
            tooltips=self.tooltips_speed_variance,
            active_drag='box_zoom',
        )

        self.f_time_diff = figure(
            title='时间差 - 上一圈与参考圈',
            x_range=self.f_speed.x_range,
            y_axis_label='时间/差值',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips_timedelta,
            active_drag='box_zoom',
        )

        self.f_throttle = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='油门',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )
        self.f_braking = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='刹车',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_coasting = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='滑行',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_tires = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='轮胎速度/车速',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_rpm = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='RPM',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_gear = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='档位',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_boost = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='增压',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        self.f_yaw_rate = figure(
            x_range=self.f_speed.x_range,
            y_axis_label='横摆角速度/秒',
            width=width,
            height=int(self.f_speed.height / 2),
            tooltips=tooltips,
            active_drag='box_zoom',
        )

        for diagram in [
            self.f_speed,
            self.f_speed_variance,
            self.f_time_diff,
            self.f_throttle,
            self.f_braking,
            self.f_coasting,
            self.f_tires,
            self.f_rpm,
            self.f_gear,
            self.f_boost,
            self.f_yaw_rate,
        ]:
            hide_toolbar(diagram)

        span_zero_time_diff = bokeh.models.Span(
            location=0,
            dimension='width',
            line_color='black',
            line_dash='dashed',
            line_width=1,
        )
        self.f_time_diff.add_layout(span_zero_time_diff)

        self.f_speed_variance.xaxis.visible = False

        self.f_throttle.xaxis.visible = False

        self.f_braking.xaxis.visible = False

        self.f_coasting.xaxis.visible = False

        self.f_tires.xaxis.visible = False

        self.f_gear.xaxis.visible = False

        self.f_rpm.xaxis.visible = False

        self.f_boost.xaxis.visible = False

        self.f_yaw_rate.xaxis.visible = False

        self.source_time_diff = ColumnDataSource(data={'distance': [], 'timedelta': []})
        self.f_time_diff.line(
            x='distance',
            y='timedelta',
            source=self.source_time_diff,
            line_width=1,
            color='blue',
            line_alpha=1,
        )

        self.source_last_lap = self.add_lap_to_race_diagram('blue', '上一圈', True)

        self.source_reference_lap = self.add_lap_to_race_diagram('magenta', '参考圈', True)

        self.source_median_lap = self.add_lap_to_race_diagram('green', '中位圈', False)

        self.f_speed.legend.location = 'top_left'
        self.f_speed.legend.click_policy = 'hide'
        self.f_throttle.legend.click_policy = self.f_speed.legend.click_policy
        self.f_braking.legend.click_policy = self.f_speed.legend.click_policy
        self.f_coasting.legend.click_policy = self.f_speed.legend.click_policy
        self.f_tires.legend.click_policy = self.f_speed.legend.click_policy
        self.f_gear.legend.click_policy = self.f_speed.legend.click_policy
        self.f_rpm.legend.click_policy = self.f_speed.legend.click_policy
        self.f_boost.legend.click_policy = self.f_speed.legend.click_policy
        self.f_yaw_rate.legend.click_policy = self.f_speed.legend.click_policy

        for fig in [self.f_throttle, self.f_braking, self.f_coasting, self.f_tires, self.f_gear, self.f_rpm, self.f_boost, self.f_yaw_rate]:
            fig.legend.location = 'top_left'

        # Leave padding on the left because rpm is 4 digits and diagrams will not start at the same position otherwise
        min_border_left = 60
        self.f_time_diff.min_border_left = min_border_left
        self.f_speed.min_border_left = min_border_left
        self.f_throttle.min_border_left = min_border_left
        self.f_braking.min_border_left = min_border_left
        self.f_coasting.min_border_left = min_border_left
        self.f_tires.min_border_left = min_border_left
        self.f_gear.min_border_left = min_border_left
        self.f_rpm.min_border_left = min_border_left
        self.f_speed_variance.min_border_left = min_border_left
        self.f_boost.min_border_left = min_border_left
        self.f_yaw_rate.min_border_left = min_border_left

        self.layout = layout(
            self.f_time_diff,
            self.f_speed,
            self.f_speed_variance,
            self.f_throttle,
            self.f_yaw_rate,
            self.f_braking,
            self.f_coasting,
            self.f_tires,
            self.f_gear,
            self.f_rpm,
            self.f_boost,
        )

        self.source_speed_variance = ColumnDataSource(data={'distance': [], 'speed_variance': []})

        self.f_speed_variance.line(
            x='distance',
            y='speed_variance',
            source=self.source_speed_variance,
            line_width=1,
            color='gray',
            line_alpha=1,
            visible=True,
        )

    def add_additional_lap_to_race_diagram(self, color: str, lap: Lap, visible: bool = True):
        if self.has_additional_lap(lap):
            return None

        source = self.add_lap_to_race_diagram(color, lap.title, visible)
        source.data = lap.get_data_dict()
        self.sources_additional_laps.append(source)
        self.additional_laps.append(lap)
        return source

    def has_additional_lap(self, lap: Lap) -> bool:
        return any(additional_lap is lap for additional_lap in self.additional_laps)

    def update_fastest_laps_variance(self, laps):
        # FIXME, many many data points, mayabe reduce by the amount of laps?
        variance, fastest_laps = gt7helper.get_variance_for_fastest_laps(laps)
        self.source_speed_variance.data = variance
        return fastest_laps

    def add_lap_to_race_diagram(self, color: str, legend: str, visible: bool = True):

        # Set empty data for avoiding warnings about missing columns
        dummy_data = Lap().get_data_dict()

        source = ColumnDataSource(data=dummy_data)

        self.speed_lines.append(
            self.f_speed.line(
                x='distance',
                y='speed',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.throttle_lines.append(
            self.f_throttle.line(
                x='distance',
                y='throttle',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.braking_lines.append(
            self.f_braking.line(
                x='distance',
                y='brake',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.coasting_lines.append(
            self.f_coasting.line(
                x='distance',
                y='coast',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.tires_lines.append(
            self.f_tires.line(
                x='distance',
                y='tires',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.gears_lines.append(
            self.f_gear.line(
                x='distance',
                y='gear',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.rpm_lines.append(
            self.f_rpm.line(
                x='distance',
                y='rpm',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.boost_lines.append(
            self.f_boost.line(
                x='distance',
                y='boost',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        self.yaw_rate_lines.append(
            self.f_yaw_rate.line(
                x='distance',
                y='yaw_rate',
                source=source,
                legend_label=legend,
                line_width=1,
                color=color,
                line_alpha=1,
                visible=visible,
            )
        )

        return source

    def get_layout(self) -> Column:
        return self.layout

    def delete_all_additional_laps(self):
        # Delete all but first three in list — iterate in reverse to avoid index shifting
        self.sources_additional_laps = []
        self.additional_laps = []

        for i in range(len(self.f_speed.renderers) - 1, self.number_of_default_laps - 1, -1):
            self.f_speed.renderers.pop(i)
            self.f_throttle.renderers.pop(i)
            self.f_braking.renderers.pop(i)
            self.f_coasting.renderers.pop(i)
            self.f_tires.renderers.pop(i)
            self.f_gear.renderers.pop(i)
            self.f_rpm.renderers.pop(i)
            self.f_boost.renderers.pop(i)
            self.f_yaw_rate.renderers.pop(i)

            self.f_speed.legend.items.pop(i)
            self.f_throttle.legend.items.pop(i)
            self.f_braking.legend.items.pop(i)
            self.f_coasting.legend.items.pop(i)
            self.f_tires.legend.items.pop(i)
            self.f_gear.legend.items.pop(i)
            self.f_rpm.legend.items.pop(i)
            self.f_yaw_rate.legend.items.pop(i)
            self.f_boost.legend.items.pop(i)


def add_annotations_to_race_line(race_line: figure, last_lap: Lap, reference_lap: Lap):
    """Adds annotations such as speed peaks and valleys and the starting line to the racing line"""

    remove_all_annotation_text_from_figure(race_line)

    decorations = []
    decorations.extend(_add_peaks_and_valley_decorations_for_lap(last_lap, race_line, color='blue', offset=0))
    decorations.extend(_add_peaks_and_valley_decorations_for_lap(reference_lap, race_line, color='magenta', offset=0))
    add_starting_line_to_diagram(race_line, last_lap)

    # This is multiple times faster by adding all texts at once rather than adding them above
    # With around 20 positions, this took 27s before.
    # Maybe this has something to do with every text being transmitted over network
    race_line.center.extend(decorations)

    # Add peaks and valleys of last lap


def _add_peaks_and_valley_decorations_for_lap(lap: Lap, race_line: figure, color, offset):
    (
        peak_speed_data_x,
        peak_speed_data_y,
        valley_speed_data_x,
        valley_speed_data_y,
    ) = lap.get_speed_peaks_and_valleys()

    decorations = []

    for i in range(len(peak_speed_data_x)):
        # shift 10 px to the left
        position_x = lap.data_position_x[peak_speed_data_y[i]]
        position_y = lap.data_position_z[peak_speed_data_y[i]]

        mytext = Label(
            x=position_x,
            y=position_y,
            text_color=color,
            text_font_size='10pt',
            text_font_style='bold',
            x_offset=offset,
            background_fill_color='white',
            background_fill_alpha=0.75,
        )
        mytext.text = '▲%.0f' % peak_speed_data_x[i]

        decorations.append(mytext)

    for i in range(len(valley_speed_data_x)):
        position_x = lap.data_position_x[valley_speed_data_y[i]]
        position_y = lap.data_position_z[valley_speed_data_y[i]]

        mytext = Label(
            x=position_x,
            y=position_y,
            text_color=color,
            text_font_size='10pt',
            x_offset=offset,
            text_font_style='bold',
            background_fill_color='white',
            background_fill_alpha=0.75,
            text_align='right',
        )
        mytext.text = '%.0f▼' % valley_speed_data_x[i]

        decorations.append(mytext)

    return decorations


def remove_all_annotation_text_from_figure(f: figure):
    f.center = [r for r in f.center if not isinstance(r, Label)]


def get_fuel_map_html_table(last_lap: Lap) -> str:
    """
    Returns a html table of relative fuel map.
    :param last_lap:
    :return: html table
    """

    fuel_maps = gt7helper.get_fuel_on_consumption_by_relative_fuel_levels(last_lap)
    table = (
        '<table><tr>'
        "<th title='相对于当前设置的燃油等级'>燃油等级</th>"
        "<th title='燃油消耗量'>燃油消耗</th>"
        "<th title='此设置下剩余圈数'>剩余圈数</th>"
        "<th title='此设置下剩余时间' >剩余时间</th>"
        "<th title='此设置下与上一圈的时间差'>时间差</th></tr>"
    )
    for fuel_map in fuel_maps:
        no_fuel_consumption = fuel_map.fuel_consumed_per_lap <= 0
        line_style = ''
        if fuel_map.mixture_setting == 0 and not no_fuel_consumption:
            line_style = 'background-color:rgba(0,255,0,0.5)'
        table += (
            "<tr id='fuel_map_row_%d' style='%s'>"
            "<td style='text-align:center'>%d</td>"
            "<td style='text-align:center'>%d</td>"
            "<td style='text-align:center'>%.1f</td>"
            "<td style='text-align:center'>%s</td>"
            "<td style='text-align:center'>%s</td>"
            '</tr>'
            % (
                fuel_map.mixture_setting,
                line_style,
                fuel_map.mixture_setting,
                0 if no_fuel_consumption else fuel_map.fuel_consumed_per_lap,
                0 if no_fuel_consumption else fuel_map.laps_remaining_on_current_fuel,
                '无燃油'
                if no_fuel_consumption
                else (gt7helper.seconds_to_lap_time(fuel_map.time_remaining_on_current_fuel / 1000)),
                '无消耗' if no_fuel_consumption else (gt7helper.seconds_to_lap_time(fuel_map.lap_time_diff / 1000)),
            )
        )
    table += '</table>'
    table += '<p>剩余燃油: <b>%d</b></p>' % last_lap.fuel_at_end
    return table


def add_starting_line_to_diagram(race_line: figure, last_lap: Lap):

    if len(last_lap.data_position_z) == 0:
        return

    x = last_lap.data_position_x[0]
    y = last_lap.data_position_z[0]

    # We use a text because scatters are too memory consuming
    # and cannot be easily removed from the diagram
    mytext = Label(
        x=x,
        y=y,
        text_font_size='10pt',
        text_font_style='bold',
        background_fill_color='white',
        background_fill_alpha=0.25,
        text_align='center',
    )
    mytext.text = '===='
    race_line.center.append(mytext)


def get_speed_peak_and_valley_diagram(last_lap: Lap, reference_lap: Lap) -> str:
    """
    Returns a html div with the speed peaks and valleys of the last lap and the reference lap
    as a formatted html table
    :param last_lap: Lap
    :param reference_lap: Lap
    :return: html table with peaks and valleys
    """
    table = """<table style='border-spacing: 10px; text-align:center'>"""

    table += """<colgroup>
    <col/>
    <col style='border-left: 1px solid #cdd0d4;'/>
    <col/>
    <col/>
    <col style="background-color: lightblue;"/>
    <col/>
    <col/>
    <col/>
    <col style="background-color: thistle;"/>
    <col/>
  </colgroup>"""

    ll_tuple_list = gt7helper.get_peaks_and_valleys_sorted_tuple_list(last_lap)
    rl_tuple_list = gt7helper.get_peaks_and_valleys_sorted_tuple_list(reference_lap)

    max_data = max(len(ll_tuple_list), len(rl_tuple_list))

    table += '<tr>'

    table += '<th></th>'
    table += '<th colspan="4">%s - %s</th>' % ('上一圈', last_lap.title)
    table += '<th colspan="4">%s - %s</th>' % ('参考圈', reference_lap.title)
    table += '<th colspan="2">差值</th>'

    table += '</tr>'

    table += """<tr>
    <td></td><td>#</td><td></td><td>位置</td><td>速度</td>
    <td>#</td><td></td><td>位置</td><td>速度</td>
    <td>位置</td><td>速度</td>
    </tr>"""

    rl_and_ll_are_same_size = len(ll_tuple_list) == len(rl_tuple_list)

    i = 0
    while i < max_data:
        diff_pos = 0
        diff_speed = 0

        if rl_and_ll_are_same_size:
            diff_pos = ll_tuple_list[i][1] - rl_tuple_list[i][1]
            diff_speed = ll_tuple_list[i][0] - rl_tuple_list[i][0]

            if diff_speed > 0:
                diff_style = f'color: rgba(0, 0, 255, .3)'  # Blue
            elif diff_speed >= -3:
                diff_style = f'color: rgba(0, 255, 0, .3)'  # Green
            elif diff_speed >= -10:
                diff_style = f'color: rgba(251, 192, 147, .3)'  # Orange
            else:
                diff_style = f'color: rgba(255, 0, 0, .3)'  # Red

        else:
            diff_style = f'text-color: rgba(255, 0, 0, .3)'  # Red

        table += '<tr>'
        table += f'<td style="width:15px; text-opacity:0.5; {diff_style}">█</td>'

        if len(ll_tuple_list) > i:
            table += f"""<td>{i + 1}</td>
                <td>{'S' if ll_tuple_list[i][2] == gt7helper.PEAK else 'T'}</td>
                <td>{ll_tuple_list[i][1]:d}</td>
                <td>{ll_tuple_list[i][0]:.0f}</td>
            """

        if len(rl_tuple_list) > i:
            table += f"""<td>{i + 1}</td>
                <td>{'S' if rl_tuple_list[i][2] == gt7helper.PEAK else 'T'}</td>
                <td>{rl_tuple_list[i][1]:d}</td>
                <td>{rl_tuple_list[i][0]:.0f}</td>
            """

        if rl_and_ll_are_same_size:
            table += f"""
                <td>{diff_pos:d}</td>
                <td>{diff_speed:.0f}</td>
            """
        else:
            table += f"""
                <td>-</td>
                <td>-</td>
            """

        table += '</tr>'
        i += 1

    table += '</td>'
    table += '<td>'

    table += '</td>'

    table = table + """</table>"""
    return table


def get_speed_peak_and_valley_diagram_row(
    peak_speed_data_x, peak_speed_data_y, table, valley_speed_data_x, valley_speed_data_y
):
    row = ''

    row += '<tr><th>#</th><th>峰值</th><th>位置</th></tr>'
    for i, dx in enumerate(peak_speed_data_x):
        row += '<tr><td>%d.</td><td>%d kph</td><td>%d</td></tr>' % (
            i + 1,
            peak_speed_data_x[i],
            peak_speed_data_y[i],
        )
    row += '<tr><th>#</th><th>谷值</th><th>位置</th></tr>'
    for i, dx in enumerate(valley_speed_data_x):
        row += '<tr><td>%d.</td><td>%d kph</td><td>%d</td></tr>' % (
            i + 1,
            valley_speed_data_x[i],
            valley_speed_data_y[i],
        )
    return row


class CornerAnalysis:
    def __init__(self, width=400):
        # Consistency bar chart
        self.source_consistency = ColumnDataSource(
            data={
                'segment': [],
                'mean_speed': [],
                'speed_std': [],
            }
        )
        self.f_consistency = figure(
            title='弯道速度一致性（每段标准差）',
            x_axis_label='赛道段',
            y_axis_label='速度标准差 (km/h)',
            width=width,
            height=250,
            tooltips=[
                ('段', '@segment'),
                ('标准差', '@speed_std{0.1f} km/h'),
                ('平均速度', '@mean_speed{0.0f} km/h'),
            ],
            active_drag='box_zoom',
        )
        self.f_consistency.vbar(
            x='segment',
            top='speed_std',
            source=self.source_consistency,
            width=0.8,
            color='steelblue',
        )
        hide_toolbar(self.f_consistency)

        # Theoretical best comparison chart
        self.source_theoretical = ColumnDataSource(
            data={
                'segment': [],
                'best_time': [],
                'theoretical_time': [],
                'time_diff': [],
            }
        )
        self.f_theoretical = figure(
            title='理论最佳 vs 实际最佳（每段）',
            x_axis_label='赛道段',
            y_axis_label='时间 (ms)',
            width=width,
            height=250,
            tooltips=[
                ('段', '@segment'),
                ('实际最佳', '@best_time{0.0f} ms'),
                ('理论最佳', '@theoretical_time{0.0f} ms'),
                ('差值', '@time_diff{+0.0f} ms'),
            ],
            active_drag='box_zoom',
        )
        self.f_theoretical.vbar(
            x=dodge('segment', -0.15, range=self.f_theoretical.x_range),
            top='best_time',
            source=self.source_theoretical,
            width=0.3,
            color='magenta',
            legend_label='实际最佳',
        )
        self.f_theoretical.vbar(
            x=dodge('segment', 0.15, range=self.f_theoretical.x_range),
            top='theoretical_time',
            source=self.source_theoretical,
            width=0.3,
            color='green',
            legend_label='理论最佳',
        )
        self.f_theoretical.legend.click_policy = 'hide'
        hide_toolbar(self.f_theoretical)

        # Summary text
        self.summary_div = Div(width=width, height=60)

        self.layout = layout(
            [
                [self.f_consistency, self.summary_div],
                [self.f_theoretical],
            ]
        )

    def update(self, laps):
        result = gt7helper.compute_segment_analysis(laps)
        if result[0] is None:
            self.f_consistency.title.text = '弯道一致性（需要 2+ 圈）'
            self.f_theoretical.title.text = '理论最佳（需要 2+ 圈）'
            self.source_consistency.data = {
                'segment': [],
                'mean_speed': [],
                'speed_std': [],
            }
            self.source_theoretical.data = {
                'segment': [],
                'best_time': [],
                'theoretical_time': [],
                'time_diff': [],
            }
            self.summary_div.text = ''
            return

        consistency_df, theoretical_time_ms, best_time_ms, theoretical_df = result

        self.source_consistency.data = ColumnDataSource.from_df(consistency_df)
        self.f_consistency.title.text = '弯道速度一致性（每段标准差）'

        self.source_theoretical.data = ColumnDataSource.from_df(theoretical_df)
        self.f_theoretical.title.text = '理论最佳 vs 实际最佳（每段）'

        delta = theoretical_time_ms - best_time_ms
        gain = gt7helper.seconds_to_lap_time(abs(delta) / 1000)
        sign = '+' if delta >= 0 else '-'
        self.summary_div.text = (
            f'<b>理论最佳:</b> {gt7helper.seconds_to_lap_time(theoretical_time_ms / 1000)}'
            f' &nbsp;|&nbsp; '
            f'<b>实际最佳:</b> {gt7helper.seconds_to_lap_time(best_time_ms / 1000)}'
            f' &nbsp;|&nbsp; '
            f'<b>差距:</b> {sign}{gain}'
        )
