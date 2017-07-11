from matplotlib import pyplot
import numpy

class solver:
    def __init__(self, x0, x1, xres, y0, y1, yres, substepx=1, substepy=1):
        """ 
        2D partial differential equation solver.
        
        Parameters
        ----------
        x0 : float
            X axis lower bound.
        x1 : float
            X axis upper bound.
        xres : integer
            Resolution of solution along the x axis.
        x0 : float
            Y axis lower bound.
        x1 : float
            Y axis upper bound.
        xres : integer
            Resolution of solution along the y axis.
        substepx : integer
            Number of intermediat steps per x axis data point.
        substepy : integer
            Number of intermediat steps per y axis data point.
        """
        self.x0 = x0
        self.x1 = x1
        self.xres = xres
        self.substepx = substepx
        self.y0 = y0
        self.y1 = y1
        self.yres = yres
        self.substepy = substepy
        
        #format self.data[x][y]
        self.x = numpy.linspace(self.x0, self.x1, self.xres*self.substepx, True)
        self.dx = (self.x1 - self.x0)/(self.xres*self.substepx - 1)
        self.y = numpy.linspace(self.y0, self.y1, self.yres*self.substepy, True)
        self.dy = (self.y1 - self.y0)/(self.yres*self.substepy - 1)
        self.data = numpy.zeros((self.xres, self.yres))
        self.axis = (self.x[::self.substepx], self.y[::self.substepy])
        
        #Assuming the folowing: self.U.shape == (n, self.xres*self.substepx) where n >= 1
        self.U = None

    def solve(self, initalization_callback, function_callback):
        """ 
        Solve the NPDE (d/dt)U(x, t) = function_callback(x, t, U).
        
        Parameters
        ----------
        initalization_callback : function(self)
            This function initalizes the solvers self.U array and takes the solver instance as the argument self.
        function_callback : function(self, array x, float y, ndarray U)
            This function defines the system of equations (d/dt)U(x, t, U). The returned array must have the shape (n, self.xres*self.substepx) where n >= 1.
        """
        initalization_callback(self)
        self.data[:, 0] = self.U[0, ::self.substepx]
        for i in range(1, self.yres*self.substepy):
            y = self.y0 + self.dy*i
            self.U = self.integrate_y(y, self.U, function_callback)
            if i % self.substepy == 0:
                self.data[:, i//self.substepy] = self.U[0, ::self.substepx]
    
    def derivative(self, profile):
        """ 
        Calculate the x derivative.
        
        Parameters
        ----------
        profile : ndarray
            The profile to differentiate.
        """
#        output = -(numpy.roll(profile, 1) - numpy.roll(profile, -1))/(2*self.dx)
        output = -(-numpy.roll(profile, 2) + 8*numpy.roll(profile, 1) - 8*numpy.roll(profile, -1) + numpy.roll(profile, -2))/(12*self.dx)
        return output

    def integrate_y(self, y, U, function_callback):
        output = U + function_callback(self, self.x, y, U)*self.dy
#        k1 = function_callback(self, self.x, y, U)
#        k2 = function_callback(self, self.x, y + self.dy/2, U + k1*self.dy/2)
#        k3 = function_callback(self, self.x, y + self.dy/2, U + k2*self.dy/2)
#        k4 = function_callback(self, self.x, y + self.dy, U + k3*self.dy)
#        output = U + (k1 + 2*k2 + 2*k3 + k4)*self.dy/6
        return output

    def integrate_x(self, y, inital_value, U, function_callback, *args):
        output = numpy.zeros((len(inital_value), self.xres*self.substepx))
        output[:, 0] = inital_value
        for i in range(1, self.xres*self.substepx):
            x = self.x0 + self.dx*i
            output[:, i] = output[:, i - 1] + function_callback(self, x, y, U[:, i - 1], output[:, i - 1], *[arg[:, i - 1] for arg in args])*self.dx
            # warning Assuming U[] and args[] are constant along x
#            k1 = function_callback(self, x, y, U[:, i - 1], output[:, i - 1], *[arg[:, i - 1] for arg in args])
#            k2 = function_callback(self, x + self.dx/2, y, U[:, i - 1], output[:, i - 1] + k1*self.dx/2, *[arg[:, i - 1] for arg in args])
#            k3 = function_callback(self, x + self.dx/2, y, U[:, i - 1], output[:, i - 1] + k2*self.dx/2, *[arg[:, i - 1] for arg in args])
#            k4 = function_callback(self, x + self.dx, y, U[:, i - 1], output[:, i - 1] + k3*self.dx, *[arg[:, i - 1] for arg in args])
#            output[:, i] = output[:, i - 1] + (k1 + 2*k2 + 2*k3 + k4)*self.dx/6
        return output

def init(self):
    a = 2*numpy.pi/(self.x1 - self.x0)
##    self.U = numpy.zeros((1, self.xres*self.substepx))
    self.U = numpy.zeros((2, self.xres*self.substepx))
#    self.U[0] = numpy.exp(-self.x**2)
#    self.U[1] = -2*self.x*numpy.exp(-self.x**2)
    self.U[0] = numpy.cos(2*a*self.x) + numpy.cos(5*a*self.x)
    self.U[1] = -2*a*numpy.sin(4*a*self.x) - 5*a*numpy.sin(5*a*self.x)
#    self.V[0] = 4*a*numpy.sin(4*a*self.y) + 7*a*numpy.sin(7*a*self.y)
#    self.V[1] = numpy.cos(4*a*self.y) + numpy.cos(7*a*self.y)

def func(self, x, y, U):
    output = numpy.zeros(shape=U.shape)
    boundary = numpy.array([numpy.exp(-y**2), -2*y*numpy.exp(-y**2)])

    U_x = self.derivative(U)
    U_xx = self.derivative(U_x)
    
    def func2(self, x, y, U, V, U_x, U_xx):
        output = numpy.zeros(shape=V.shape)
        output[:-1] = V[1:]
        output[-1] = (V[0] - U_xx[0] - U_x[0]*U[1])/(U[0]**2 + 10)
        return output
    
    u_tm = self.integrate_x(y, boundary, U, func2, U_x, U_xx)[0, :]
    output[:-1] = U[1:]
    output[-1] = u_tm

##    output[0] = U[0]*self.derivative(U[0])
#    output[0] = self.derivative(U[0])**2 - self.derivative(U[0])
    
#    output[0] = U[1]
#    output[1] = -U[0]*self.derivative(U[1]) + U[1]*self.derivative(U[0])

#    output[0] = U[1]
#    output[1] = self.derivative(self.derivative(U[0]))
    return output

A = solver(-3, 3, 200, 0, 4, 200, 2, 4)
A.solve(init, func)

pyplot.plot(A.axis[0], A.data[:, 0])
pyplot.show()
#pyplot.imshow(A.data[::1, ::1], clim=(-1, 1))
#pyplot.show()
pyplot.imshow(A.data)
pyplot.show()
