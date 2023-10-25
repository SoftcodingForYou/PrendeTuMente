#Prepare userland =========================================================
from multiprocessing                        import Process, Pipe
from PyQt5                                  import QtWidgets, QtCore, QtGui
from pyqtgraph                              import PlotWidget, plot
from numpy                                  import abs, where, ones
import time
import pyqtgraph                            as pg
from backend                                import Backend
from digital_signal_processing              import Processing
import sys  # We need sys so that we can pass argv to QApplication
import os
import serial #Crucial: Install using pip3 install "pyserial", NOT "serial"
import serial.tools.list_ports

class Frontend(QtWidgets.QMainWindow, Processing):

    def __init__(self, *args, **kwargs):

        bkn                 = Backend()

        # Load parameters
        # -----------------------------------------------------------------
        self.port           = str(input("Which COM port is the arduino connected to?: "))
        self.baud_rate      = 115200
        self.numsamples     = int(bkn.sample_rate * bkn.buffer_length)
        self.numchans       = bkn.num_channels
        self.left_edge      = int(bkn.buffer_add)
        self.count          = 0
        self.s_down         = bkn.downsampling
        self.idx_retain     = range(0, int(bkn.sample_rate * bkn.buffer_length), bkn.downsampling)
        self.yrange         = bkn.yrange
        self.maxvalue       = 2500
        self.last_trigger   = False

        # Load methods
        # -----------------------------------------------------------------
        self.conn_socket    = bkn.prepare_socket(bkn.ip, bkn.port)

        # Generate variable exchange pipe
        # -----------------------------------------------------------------
        self.recv_conn, self.send_conn = Pipe(duplex = False)

        # Generate separate processes to not slow down sampling by any
        # other executions
        # -----------------------------------------------------------------
        self.sampling    = Process(target=bkn.fill_buffer,
            args=(self.send_conn, self.conn_socket))
        
        self.sampling.start()

        # Build GUI
        # -----------------------------------------------------------------
        super(Frontend, self).__init__(*args, **kwargs)

        self.setWindowTitle("Neuri workshop")
        
        # This following line causes and X11 error on GNU/Linux (tried with
        # various distributions)
        # self.setWindowIcon(QtGui.QIcon(pm.img_helment))
        
        self.central_widget = QtWidgets.QWidget() # A QWidget to work as Central Widget

        # Without specifying, this just makes the GUI separable vertically
        # and horizontally 
        vertlayout          = QtWidgets.QHBoxLayout() # Vertical Layout
        controlpanel        = QtWidgets.QHBoxLayout() # Horizontal Layout

        # Load frontend elements
        widget_amp_threshold= QtWidgets.QWidget()
        amplayout           = QtWidgets.QVBoxLayout() # Horizontal Layout

        init_value          = self.maxvalue*0.9
        self.amp_title      = QtWidgets.QLabel(str(init_value))

        ampSlider           = QtWidgets.QSlider(QtCore.Qt.Vertical)
        ampSlider.setTickPosition(QtWidgets.QSlider.TicksBothSides)

        ampSlider.setMinimum(0)
        ampSlider.setMaximum(self.maxvalue)

        ampSlider.setSingleStep(10)

        ampSlider.valueChanged.connect(self.value_changed)
        ampSlider.sliderMoved.connect(self.slider_position)

        amplayout.addWidget(ampSlider)
        amplayout.addWidget(self.amp_title)
        amplayout.addWidget(QtWidgets.QLabel("            ")) # This just assures width of the layout
        amplayout.geometry().width()
        widget_amp_threshold.setLayout(amplayout)

        self.graphWidget    = PlotWidget()
        vertlayout.addWidget(self.graphWidget)
        controlpanel.addWidget(widget_amp_threshold)
        vertlayout.addLayout(controlpanel)

        # Finalize
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(vertlayout) # Draw elements in main widget

        # Real-time plotting
        self.timer = QtCore.QTimer()
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.singleShot = False

        # Decorate
        self.graphWidget.setBackground('transparent')
        self.graphWidget.setYRange(self.yrange[0], self.yrange[1])
        self.graphWidget.setRange(yRange=(self.yrange[0], self.yrange[1]), disableAutoRange=True)
        self.graphWidget.setLabel('left', 'Amplitude de señal')
        self.graphWidget.setLabel('bottom', 'Tiempo (segundos)')
        self.graphWidget.addLegend()
        self.set_theme()

        pen1 = pg.mkPen(color=(20, 30, 70), width=1.5)
        pen2 = pg.mkPen(color=(199, 0, 57), width=1.5)

        # Antialiasing decreases performance: Set False if too slow
        self.graphWidget.setAntialiasing(True)

        self.create_forward_port()
        
        # Protect potentially breaking parts in safety net which will close
        # connections when errors are encountered
        try:
            
            ampSlider.setValue(int(round(init_value)))
            ampSlider.setTickInterval(int(round(self.maxvalue/50)))

            self.x = list(range(-self.numsamples, 0, self.s_down))
            self.x = [x/bkn.sample_rate for x in self.x]
            self.y = [0 for _ in range(0, self.numsamples, self.s_down)]

            self.data_line = {}
            self.data_line[0] =  self.graphWidget.plot(self.x, self.y, name='Corazón', pen=pen1)
            self.data_line[1] =  self.graphWidget.plot(self.x, self.y, name='Umbral', pen=pen2)

            # Disable interactivity
            self.graphWidget.setMouseEnabled(x=False, y=False)
            self.graphWidget.hideButtons()
            self.graphWidget.getPlotItem().setMenuEnabled(False)
            
            self.graphWidget.mouseDragEvent = lambda *args, **kwargs: None
            self.graphWidget.hoverEvent = lambda *args, **kwargs: None
            
            self.sendser.open()
            self.timer.start()
            print('Starting... Window may seem non-responsive for some seconds')

        except:
            
            print('Something went wrong. Initializing closing sequence...')
            self.on_closing()
            time.sleep(2)
            print('Quit now. This is the last output')
            quit()


    def update_plot_data(self):

        # Update plots for every channel
        # -----------------------------------------------------------------
        buffer, t_now       = self.recv_conn.recv()

        self.count = self.count + 1
        if self.count < self.s_down:
            return

        # Filter buffer signal and send filtered data to plotting funcs
        # -------------------------------------------------------------
        processed_buffer    = self.prepare_buffer(buffer,
            self.b_notch, self.a_notch, self.b_workshop, self.a_workshop)
        processed_buffer    = processed_buffer[:, self.left_edge:]

        processed_buffer    = abs(processed_buffer)

        self.x              = self.x[1:]  # Remove the first y element
        self.x.append(self.x[-1]+self.count/self.sample_rate) # t_now/1000

        self.y              = processed_buffer[0, self.idx_retain]
        self.data_line[0].setData(self.x, self.y)  # Update the data

        # Plot threshold
        self.data_line[1].setData(self.x, ones(len(self.x))*self.yrange[1])
        # self.graphWidget.setYRange(self.yrange[0], self.yrange[1])
        self.graphWidget.setYRange(0, self.maxvalue)

        # Search for threshold crossing and send trigger if so
        self.decide_trgigger(self.y)

        self.count          = 0


    def search_ports(self):

        self.ports = list(serial.tools.list_ports.comports())


    def create_forward_port(self):

        self.sendser                = serial.Serial()
        self.sendser.port           = self.port
        self.sendser.baudrate       = self.baud_rate
        self.sendser.timeout        = None
        self.sendser.write_timeout  = None


    def close_forward_port(self):

        self.sendser.close()


    def decide_trgigger(self, signal):

        above_thr           = where(signal >= self.yrange[1])[0]
        below_thr           = where(signal < self.yrange[1])[0]

        if below_thr.size == 0:
            trigger         = True
        elif above_thr.size == 0 or above_thr[-1] < below_thr[-1]:
            trigger         = False
        else:
            trigger         = True            

        if trigger != self.last_trigger:
            if trigger:
                # self.graphWidget.setBackground((255, 105, 105))
                self.sendser.write(bytes("H", 'utf-8'))
            else:
                # self.graphWidget.setBackground('transparent')
                self.sendser.write(bytes("L", 'utf-8'))
            self.setPalette(self.palette)
            self.last_trigger = trigger


    def value_changed(self, i):
        self.yrange = [-i, i]
        self.amp_title.setText(str(i))


    def slider_position(self, i):
        self.yrange = [-i, i]
        self.amp_title.setText(str(i))


    def set_theme(self):

        base        = (255, 245, 224) # Yellowish cream
        text        = (20, 30, 70) # 
        highlight   = (255, 105, 105) # 


        self.palette = QtGui.QPalette()
        self.palette.setColor(QtGui.QPalette.Window,         QtGui.QColor(base[0], base[1], base[2]))
        self.palette.setColor(QtGui.QPalette.Base,           QtGui.QColor(base[0], base[1], base[2]))
        self.palette.setColor(QtGui.QPalette.AlternateBase,  QtGui.QColor(base[0], base[1], base[2]))
        self.palette.setColor(QtGui.QPalette.ToolTipBase,    QtGui.QColor(text[0], text[1], text[2]))
        self.palette.setColor(QtGui.QPalette.Text,           QtGui.QColor(text[0], text[1], text[2]))
        self.palette.setColor(QtGui.QPalette.Button,         QtGui.QColor(highlight[0], highlight[1], highlight[2]))
        self.palette.setColor(QtGui.QPalette.ButtonText,     QtGui.QColor(text[0], text[1], text[2]))
        self.palette.setColor(QtGui.QPalette.BrightText,     QtGui.QColor(base[0], base[1], base[2]))
        self.palette.setColor(QtGui.QPalette.Highlight,      QtGui.QColor(text[0], text[1], text[2]))
        self.palette.setColor(QtGui.QPalette.HighlightedText,QtGui.QColor(text[0], text[1], text[2]))
        self.setPalette(self.palette)


    def on_closing(self):
        self.timer.stop()
        self.sampling.terminate()
        self.conn_socket.close()
        self.recv_conn.close()
        self.send_conn.close()


if __name__ == '__main__': # Necessary line for "multiprocessing" to work
    
    app                     = QtWidgets.QApplication(sys.argv)
    maingui                 = Frontend()

    maingui.show()
    app.exec_()
    maingui.on_closing()
    sys.exit()  # Proper way would be "sys.exit(app.exec_())" but it does  
                # not return the main console

