Failed:
        await audit(
            session,
            request,
            title="Login failed",
            entity_type=EntityType.USER,
            entity_id=0,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.FAILED,
            error_message="Invalid credentials",
            meta={"username": form.username},
        )




    Success


        await audit(
            session,
            request,
            title="User login",
            entity_type=EntityType.USER,
            entity_id=user.id,
            action=ActivityAction.LOGIN,
            outcome=ActivityOutcome.SUCCESS,
            actor_id=user.id,
            actor_first_name=user.first_name,
            meta={"username": user.username},
        )
