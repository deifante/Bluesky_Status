class IstockRouter(object):
    """
    A router to control reads from the iStock reporting db
    """
    # This feels a little kludgy. It'd be cool if this was automatic and
    # read directly from the mysql_access to determine the classes there.
    # On the other hand, that might be a little slow to execute on *every*
    # db look up.
    ISTOCK_MODELS = ['abstractfile', 'exclusivityuser', 'abstractfiletaxonomy',
                     'abstractfiletaxonomylog', 'abstractfiletypegroup',
                     'filetaxonomy', 'user', 'agencycontributorxuser']
    def db_for_read(self, model, **hints):
        """
        It'd be great if I could just get the
        """
        # This *cannot* be the best way to do this
        model_name = str(model._meta).split('.')[1]
        if model_name in IstockRouter.ISTOCK_MODELS:
            return 'istock'
        return None

    # Making writes go to the default db will ensure we're not
    # touching iStock live database.
    # def db_for_write(self, model, **hints):
    #     pass
