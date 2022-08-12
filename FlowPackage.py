import pandas as pd
import vaex
import math
import plotly.express as px
import plotly.graph_objects as go


def degree2Float(degree=0, minute=0, second=0):
    """
        坐标经纬度角度转浮点数
        Example In: 29, 44.765 -> (29°44.765'N )
        Example Return: 29.746083
    """
    result = 0
    if degree:
        result = degree
    if minute:
        result += minute / 60
    if second:
        result += second / 3600
    return round(result, 6)


def getLineSlope(lat1, lon1, lat2, lon2):
    """
        得到门线斜率
        Example In: 29.746083, 122.341683, 29.729083, 122.3307
        Example Return: 2.9144522544095754
    """
    doorLineSlope = (lat2 - lat1) / (lon2 - lon1)
    return doorLineSlope


def getSquareDiagonal(lat1, lon1, lat2, lon2):
    """
        得到以门线为正方形斜边的区域四个顶点坐标
    """
    doorLineDiagonal = getLineSlope(lat1, lon1, lat2, lon2)
    anotherLineDiagonal = -1 / doorLineDiagonal
    halfDoorLineLength = pow((lat1 - lat2)**2 + (lon1 - lon2)**2, 0.5)
    halfDoorLinePoint = [(lat1 + lat2) / 2, (lon1 + lon2) / 2]
    lon3 = lon1 + pow(halfDoorLineLength**2 / (anotherLineDiagonal + 1), 0.5)
    lon4 = lon2 - pow(halfDoorLineLength**2 / (anotherLineDiagonal + 1), 0.5)
    quarterArea = (lat1 - halfDoorLinePoint[0]) * (lon1 - halfDoorLinePoint[1])
    # (lat3 - halfDoorLinePoint[0]) * (lon3 - halfDoorLinePoint[1]) = quarterArea
    lat3 = round(
        quarterArea / (lon3 - halfDoorLinePoint[1]) + halfDoorLinePoint[0], 6)
    lat4 = round(
        quarterArea / (lon4 - halfDoorLinePoint[1]) + halfDoorLinePoint[0], 6)
    lon3 = round(lon3, 6)
    lon4 = round(lon4, 6)
    result = pd.DataFrame([(lat1, lon1), (lat3, lon3), (lat2, lon2),
                           (lat4, lon4), (lat1, lon1)],
                          columns=['lat', 'lon'])
    return result


def haversine(lat1, lon1, lat2, lon2):
    """
        haversine公式：计算两经纬度点之间的距离 结果单位千米 已转换为海里
    """
    R = 6371
    latDiff = (lat2 - lat1) * math.pi / 180.0
    lonDiff = (lon2 - lon1) * math.pi / 180.0
    a = math.sin(latDiff / 2) * math.sin(latDiff / 2) + math.cos(lat1 * math.pi / 180.0) * \
        math.cos(lat2 * math.pi / 180.0) * \
        math.sin(lonDiff / 2) * math.sin(lonDiff / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = (R * c) / 1.852
    return distance


def getLineCourse(LineSlope: float):
    """
        斜率->弧度->角度: 得到门线与水平线/纬线的夹角
    """
    doorLineDegree = (math.degrees(math.atan(LineSlope)) + 180) % 180
    return doorLineDegree


def filterCourse(data: pd.DataFrame, upCourseRange: int, downCourseRange: int,doorLinePoints: pd.DataFrame):
    """
        根据航向过滤通过门线的船舶
    """
    baseCourse = getLineCourse(
        getLineSlope(doorLinePoints.lat[0], doorLinePoints.lon[0],
                     doorLinePoints.lat[1], doorLinePoints.lon[1]))
    # 由船舶与门线的夹角转换至船舶真航向角度（自正北顺时针起） 需要累加一个角度值addCourse
    # 如果门线与水平线/纬线的夹角大于90度 通过门线的船舶真航向角度在理论上应该位于第一象限和第三象限
    if baseCourse > 90:
        addCourse = [180, 0]
    # 如果门线与水平线/纬线的夹角小于90度 通过门线的船舶真航向角度在理论上应该位于第二象限和第四象限
    else:
        addCourse = [270, 90]
    upStreamCourse = (90 - baseCourse + addCourse[0] + 360) % 360
    downStreamCourse = (90 - baseCourse + addCourse[1] + 360) % 360
    upStreamCourseLower = (upStreamCourse - upCourseRange / 2)
    upStreamCourseUpper = (upStreamCourse + upCourseRange / 2)
    downStreamCourseLower = (downStreamCourse - downCourseRange / 2)
    downStreamCourseUpper = (downStreamCourse + downCourseRange / 2)
    data = data[((data['cog'] > upStreamCourseLower) &
                 (data['cog'] < upStreamCourseUpper)) |
                ((data['cog'] > downStreamCourseLower) &
                 (data['cog'] < downStreamCourseUpper))]
    data.reset_index(drop=True, inplace=True)
    upStreamData = data[(data['cog'] > upStreamCourseLower)
                        & (data['cog'] < upStreamCourseUpper)]
    downStreamData = data[(data['cog'] > downStreamCourseLower)
                          & (data['cog'] < downStreamCourseUpper)]
    return data, upStreamData, downStreamData

def PlotDoorLineArea(token,squarePoints: pd.DataFrame,doorLinePoints: pd.DataFrame,areaName:str,doorLineName:str):

    # 使用getSquareDiagonal函数得到以门线为正方形斜边的区域四个顶点坐标
    fig = px.line_mapbox(squarePoints, lat="lat", lon="lon", zoom=10)
    # 添加正方形区域轨迹
    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=squarePoints.lon,
                         lat=squarePoints.lat,
                         name=areaName,
                         marker={'size': 9}))

    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=doorLinePoints.lon,
                         lat=doorLinePoints.lat,
                         name=doorLineName,
                         marker={'size': 9}))
    fig.update_layout(title={
        'text': areaName,
        'font_color': '#FF0000',
        'font_size': 25,
        'x': 0.01,
        'y': 0.95},
        mapbox={'accesstoken': token,
                'center':
                    {
                        'lon': doorLinePoints.lon[1],
                        'lat': doorLinePoints.lat[1]
                    },
                'style': "basic",
                'zoom': 11},
        margin={'l': 0,
                'r': 0,
                't': 0,
                'b': 0
                },
        width=1000,
        height=500)
    fig.show()


def PlotTraceAll(token,dfLonLatCog:pd.DataFrame,doorLinePoints,areaName:str,doorLineName:str):
    '''
    用于绘制整个门线区域内的轨迹图(不区分上下游)
    :param df: 需要统计的数据
    :param doorlinePoint: 门线坐标列表
    :return:
    '''

    fig = px.scatter_mapbox(dfLonLatCog, lat="lat", lon="lon", zoom=10)
    # 添加正方形区域轨迹
    fig.update_layout(title={
        'text': areaName,
        'font_color': '#FF0000',
        'font_size': 25,
        'x': 0.01,
        'y': 0.95},
        mapbox={
            'accesstoken': token,
            'center': {
                'lon': doorLinePoints.lon[1],
                'lat': doorLinePoints.lat[1]
            },
            'style': "basic",
            'zoom': 12
        },
        margin={
            'l': 0,
            'r': 0,
            't': 0,
            'b': 0
        },
        width=1000,
        height=500)
    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=doorLinePoints.lon,
                         lat=doorLinePoints.lat,
                         name=doorLineName,
                         marker={'size': 9}))
    fig.show()

def PlotTraceOfUpstreamAndDownStream(token,doorLinePoints,upStreamData,downStreamData,areaName:str,doorLineName:str):
    '''
    画上下游通过门线数据总图
    :param token:
    :param doorLinePoints:
    :param upStreamData:
    :param downStreamData:
    :return:
    '''
    fig = go.Figure()
    # 添加正方形区域轨迹
    fig.update_layout(title={
        'text': areaName,
        'font_color': '#FF0000',
        'font_size': 25,
        'x': 0.01,
        'y': 0.95
    },
        mapbox={
            'accesstoken': token,
            'center': {
                'lon': doorLinePoints.lon[1],
                'lat': doorLinePoints.lat[1]
            },
            'style': "basic",
            'zoom': 12
        },
        margin={
            'l': 0,
            'r': 0,
            't': 0,
            'b': 0
        },
        width=1000,
        height=500)
    fig.add_trace(
        go.Scattermapbox(mode="markers",
                         lon=upStreamData.lon,
                         lat=upStreamData.lat,
                         name="流向1",
                         marker={'size': 3}))
    fig.add_trace(
        go.Scattermapbox(mode="markers",
                         lon=downStreamData.lon,
                         lat=downStreamData.lat,
                         name="流向2",
                         marker={'size': 3}))
    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=doorLinePoints.lon,
                         lat=doorLinePoints.lat,
                         name=doorLineName,
                         marker={'size': 9}))

    fig.show()

def plotTraceOfUpstream(token,doorLinePoints,upStreamData,areaName:str,doorLineName:str):
    '''
    画上游船舶通过门线轨迹图
    :param token:
    :param doorLinePoints:
    :param upStreamData:
    :return:
    '''
    fig = px.scatter_mapbox(upStreamData, lat="lat", lon="lon", zoom=10)
    # 添加正方形区域轨迹
    fig.update_layout(title={
        'text': areaName,
        'font_color': '#FF0000',
        'font_size': 25,
        'x': 0.01,
        'y': 0.95
    },
        mapbox={
            'accesstoken': token,
            'center': {
                'lon': doorLinePoints.lon[1],
                'lat': doorLinePoints.lat[1]
            },
            'style': "basic",
            'zoom': 12
        },
        margin={
            'l': 0,
            'r': 0,
            't': 0,
            'b': 0
        },
        width=1000,
        height=500)
    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=doorLinePoints.lon,
                         lat=doorLinePoints.lat,
                         name=doorLineName,
                         marker={'size': 9}))
    fig.show()

def plotTraceOfDownstream(token,doorLinePoints: pd.DataFrame,downStreamData: pd.DataFrame,areaName:str,doorLineName:str):
    '''

    :param token: plotly帐号token
    :param doorLinePoints: 门线坐标数据
    :param downStreamData: 下流通过门线数据
    :return:
    '''
    fig = px.scatter_mapbox(downStreamData, lat="lat", lon="lon", zoom=10)
    # 添加正方形区域轨迹
    fig.update_layout(title={
        'text': areaName,
        'font_color': '#FF0000',
        'font_size': 25,
        'x': 0.01,
        'y': 0.95
    },
        mapbox={
            'accesstoken': token,
            'center': {
                'lon': doorLinePoints.lon[1],
                'lat': doorLinePoints.lat[1]
            },
            'style': "basic",
            'zoom': 12
        },
        margin={
            'l': 0,
            'r': 0,
            't': 0,
            'b': 0
        },
        width=1000,
        height=500)
    fig.add_trace(
        go.Scattermapbox(mode="markers+lines",
                         lon=doorLinePoints.lon,
                         lat=doorLinePoints.lat,
                         name=doorLineName,
                         marker={'size': 9}))
    fig.show()
#传入需要检测到数据df,以及门限坐标列表doorLine
def getFilteLonLatCogData(df,squarePoints: pd.DataFrame):
    '''
     # 读取数据并转换为HDF5格式 数据大小膨胀率约为150%
    # 读取并转换的过程中会先让数据按chunk_size大小切分成若干小文件
    # 并将这若干个小文件暂存至硬盘中(同样会占据150%的空间)
    # 切分完成后 会将这若干个小文件自动合并为一个大HDF5文件 并自动删除之前的若干个小文件
    # 自动执行合并任务的过程中 会同时存在 原数据 + 若干个小文件 + 大HDF5文件
    # 所以处理4GB数据 硬盘空间至少要保留16GB 同理 处理100GB数据时 硬盘空间至少要保留400GB (i7-12700HK RTX3060 16GB内存电脑上 处理4GB数据 耗时约6分半)
    # 不要写为 df = vaex.from_csv 等语句 并且convert尽量要为True 不要对vaex.from_csv函数返回的结果进行赋值 会进一步节省内存开销
    :param df: vaex获取数据DataFrameLocal类型
    :param squarePoints: 门线区域数据
    :return: 通过门线区域的船舶数据
    '''

    # 提取vaex数据中的列
    dfMsi = df['MMSI'].to_pandas_series().values
    dfLat = df['Lat'].to_pandas_series().values
    dfLon = df['Lon'].to_pandas_series().values
    dfCog = df['Course'].to_pandas_series().values
    dfLength = df['Length'].to_pandas_series().values
    dfSpeed = df['Speed'].to_pandas_series().values

    # 数据合并为DataFrame
    dfLonLatCog = pd.DataFrame({'lat': dfLat, 'lon': dfLon, 'cog': dfCog,'mmsi':dfMsi,'length':dfLength,'speed':dfSpeed})
    # bug: 数据合并后 数据行中存在列名 找到这些行的索引并删除
    strIndexs = dfLonLatCog[dfLonLatCog['lat'] == 'Lat'].index
    dfLonLatCog.drop(index=strIndexs, axis=0, inplace=True)
    # vaex读取数据时 类型为pyarrow.lib.StringArray 合并为DataFrame后 可以很方便的转为浮点型
    dfLonLatCog = dfLonLatCog.astype('float32')
    # 直接在DataFrame上进行筛选
    dfLonLatCog = dfLonLatCog[
        (dfLonLatCog['lat'] <= squarePoints['lat'].max())
        & (dfLonLatCog['lat'] >= squarePoints['lat'].min()) &
        (dfLonLatCog['lon'] <= squarePoints['lon'].max()) &
        (dfLonLatCog['lon'] >= squarePoints['lon'].min())]
    #接着筛选(筛选重复值)
    dfLonLatCog.drop_duplicates(['mmsi','cog','lat','lon'],ignore_index=True,inplace=True)
    # 重设索引
    dfLonLatCog.reset_index(drop=True, inplace=True)
    return dfLonLatCog


def getFlowData(dfLonLatCog:pd.DataFrame,doorLinePoints: pd.DataFrame):
    '''
    用于获取过滤后的数据(流量)
    :param dfLonLatCog: 过滤过后到流量数据
    :return: 返回通过门线船舶数量
    '''
    count=0
    dataResult, upStreamData, downStreamData = filterCourse(dfLonLatCog, 180, 180,doorLinePoints)
    Result=dataResult.drop_duplicates(['mmsi'],ignore_index=True)
    mmsi=list(dataResult['mmsi'].drop_duplicates())
    # print('msi=',len(mmsi))

    if abs(doorLinePoints.lat[0]-doorLinePoints.lat[1]) <= abs(doorLinePoints.lon[0] - doorLinePoints.lon[1]):
        for m in mmsi:
            # print(m)
            msi=dataResult[ dataResult['mmsi'] == m].reset_index(drop=True)
            # print('msi=', len((msi)))
            Dmmsi=len(msi[ msi['lat'] >= doorLinePoints['lat'].max()])
            # print('D=',Dmmsi)
            Xmmsi=len((msi[ msi['lat'] < doorLinePoints['lat'].max()]))
            # print('X=',Xmmsi)
            DDmsi=len(msi[ msi['lat'] <=doorLinePoints['lat'].min()])
            # print('DD=',DDmsi)
            XXmsi=len(msi[ msi['lat'] >doorLinePoints['lat'].min()])
            # print('XX=', XXmsi)
            if (Dmmsi > 0) & (Xmmsi > 0) | (DDmsi > 0) & (XXmsi > 0) | (Xmmsi > 2) & (XXmsi > 2):
                count+=1
            else:
                lsindex = Result[Result['mmsi'] == m].index
                Result.drop(index=lsindex,inplace=True)
    else:
        for m in mmsi:
            msi=dataResult[ dataResult['mmsi'] == m ].reset_index(drop=True)
            # print('msi=',len((msi)))
            Dmmsi=len(msi[ msi['lon'] >= doorLinePoints['lon'].max()])
            # print('D=', Dmmsi)
            Xmmsi=len((msi[ msi['lon'] < doorLinePoints['lon'].max()]))
            # print('X=', Xmmsi)
            DDmsi=len(msi[ msi['lon'] <=doorLinePoints['lon'].min()])
            # print('DD=', DDmsi)
            XXmsi=len(msi[ msi['lon'] >doorLinePoints['lon'].min()])
            # print('XX=', XXmsi)
            if (Dmmsi > 0) & (Xmmsi > 0) | (DDmsi > 0) & (XXmsi > 0) | (Xmmsi > 2) & (XXmsi > 2):
                count+=1
            else:
                lsindex=Result[Result['mmsi']==m].index
                Result.drop(index=lsindex,inplace=True)
    print('总流量:',count)
    return count,Result


def getAreaSize(squarePoints:pd.DataFrame):
    '''
    计算矩形四边长度
    存在勾股定理与haversine公式之间的计算误差
    :param squarePoints:
    :return:
    '''
    for i in range(len(squarePoints) - 1):
        dis = haversine(squarePoints.iloc[i].values[0],
                    squarePoints.iloc[i].values[1],
                    squarePoints.iloc[i + 1].values[0],
                    squarePoints.iloc[i + 1].values[1])
        print('门线周围最大面积矩形框边长(海里):',dis)