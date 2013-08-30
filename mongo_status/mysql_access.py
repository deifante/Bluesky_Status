import MySQLdb

def is_partner_program(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select Collections from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    if (data):
        # Data is returned in a tuple.
        return data[0].find('GettyDistribution') != -1
    else:
        return 0

def get_file_type(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select AbstractTypeID from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    if not data:
        return None

    # Data is returned in a tuple.
    data = data[0]

    if data == 1:
        return 'photo'
    elif data == 4:
        return 'flash'
    elif data == 7:
        return 'vector'
    elif data == 8:
        return 'video'
    else:
        return None

def get_approval_time(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select ApprovalTime from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    if not data:
        return None
    # Data is returned in a tuple. The drivers turn this data into a native date

    data = data[0]
    return data

def get_upload_time(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select CreationDate from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    if not data:
        return None

    # Data is returned in a tuple. The drivers turn this data into a native date
    return data[0]

def get_file_status(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select Status from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    if data == None or data[0] == None:
        return None
    return data[0]

def get_collection(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select tbl_FileTaxonomy.Name from tbl_AbstractFileTaxonomy inner join tbl_FileTaxonomy on tbl_AbstractFileTaxonomy.FileTaxonomyID =  tbl_FileTaxonomy.ID where AbstractFileID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()

    # Only files that are not in main have an entry here.
    if data == None or data[0] == None:
        return 'Main'
    return data[0]

def get_previous_collections(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select tbl_FileTaxonomy.Name, tbl_AbstractFileTaxonomyLog.DateChanged from tbl_AbstractFileTaxonomyLog inner join tbl_FileTaxonomy on tbl_AbstractFileTaxonomyLog.NewTaxonomy = tbl_FileTaxonomy.ID where AbstractFileID = %d order by DateChanged desc' % assetId
    cursor.execute(query)
    data = cursor.fetchall()
    # Unlike in 'get_collection', entries these entires don't treat the "Main"
    # collection in a special manner.
    return [{'previous_collection_name':x[0], 'previous_collection_date_changed':x[1]} for x in data]

def get_contributor_names(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select `user`.userID, `user`.username, `user`.`first`, `user`.`last`, `user`.studio_name from `user` inner join AbstractFile on `user`.userID = AbstractFile.UserID where AbstractFile.ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()
    return {'userId':data[0], 'username':data[1], 'first':data[2], 'last':data[3], 'studio_name':data[4]}

def get_contributor_exclusivity(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select tbl_AbstractFileTypeGroup.Name from ExclusivityUser inner join tbl_AbstractFileTypeGroup on tbl_AbstractFileTypeGroup.ExclusivityID = ExclusivityUser.ExclusivityID inner join AbstractFile on AbstractFile.UserID =  ExclusivityUser.UserID where AbstractFile.ID = %d' % assetId
    cursor.execute(query)
    return cursor.fetchone()

def get_contributor_email(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select `user`.email from `user` inner join AbstractFile on `user`.userID = AbstractFile.UserID where AbstractFile.ID = %d' % assetId
    cursor.execute(query)
    
    data = cursor.fetchone()

    if not data:
        return None
        # Data is returned in a tuple.
    return data[0]
