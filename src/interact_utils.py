from ipywidgets import interactive
import ipywidgets as widgets

class NotebookInteractive:
    def __init__(self, chart_style = 'plotly'):
        if chart_style == 'plotly':
            import plotly
            plotly.offline.init_notebook_mode()
        else:
            pass
    
    def __getDefaultValue(self, arr, idx, val=0):
        try:
            return arr[idx]
        except:
            return val
    
    def __getWidgetMode(self, w):
        opts = w[0]
        des = w[1]
        mode = w[-1]
        if mode == 'slider':
            return widgets.FloatSlider(
                value=self.__getDefaultValue(opts, 3, (opts[0] + opts[1]) / 2),
                min=opts[0],
                max=opts[1],
                step=self.__getDefaultValue(opts, 2, 1),
                description=des
            )
        elif mode == 'dropdown':
            return widgets.Dropdown(
                options=opts,
                value=opts[0],
                description=des
            )
        elif mode == 'button':
            return widgets.ToggleButtons(
                options=opts,
                description=des,
                button_style='info', # 'success', 'info', 'warning', 'danger' or ''
            )
        elif mode == 'checkbox':
            return widgets.Checkbox(
                description=des,
                value=opts,
                tooltip='Click me'
            )
        elif mode == 'text':
            return widgets.Text(
                value=str(opts),
                placeholder='Type something',
                description=des
            )
        else:
            raise Exception('No widget mode specified')
    
    def __wrapperFn(self, fn):
        def inner(**kwargs):
            args = ()
            for key, val in kwargs.items():
                args += (val,)
            fn(*args)
        return inner
    
    def draw(self, fn, wdgs):
        kwargs = {}
        for i, w in enumerate(wdgs):
            kwargs[f'w{i}'] = self.__getWidgetMode(w)

        return interactive(self.__wrapperFn(fn), **kwargs)
