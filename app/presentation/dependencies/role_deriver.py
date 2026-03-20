def derive_role_flags(user):
    """
    Extract role flags from the new single-role model:
      user.role --> Role object
      user.role.name --> "ADMIN", "SUPERADMIN", etc.
    """

    # New single-role system
    if hasattr(user, "role") and user.role is not None:
        role_name = (user.role.name or "").upper()
    else:
        role_name = ""

    is_superuser = (role_name == "SUPERADMIN")
    is_admin = is_superuser or (role_name == "ADMIN")

    return {
        "role_name": role_name,
        "is_superuser": is_superuser,
        "is_admin": is_admin,
    }
