from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.presentation.schemas.program_schema import ProgramCreate, ProgramUpdate, ProgramOut
from app.core.db import get_session
from app.infrastructure.repositories.program_repository_sqlalchemy import ProgramRepository
from app.application.services.program_rules import ProgramRulesService
from app.application.use_cases.program.create_program import CreateProgramUseCase
from app.application.use_cases.program.list_programs_by_portfolio import ListProgramsByPortfolioUseCase
from app.application.use_cases.program.get_program import GetProgramUseCase
from app.application.use_cases.program.update_program import UpdateProgramUseCase
from app.application.use_cases.program.delete_program import DeleteProgramUseCase

program_router = APIRouter(tags=["Programs"])

def get_usecases(session: AsyncSession = Depends(get_session)):
    repo = ProgramRepository(session)
    rules = ProgramRulesService(session)
    return (
        CreateProgramUseCase(repo, rules),
        ListProgramsByPortfolioUseCase(repo),
        GetProgramUseCase(repo),
        UpdateProgramUseCase(repo, rules),
        DeleteProgramUseCase(repo),
        session,
    )

@program_router.post("/portfolios/{portfolio_id}/programs", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
async def create_program_for_portfolio(portfolio_id: int, payload: ProgramCreate, deps = Depends(get_usecases)):
    create_uc, *_ , session = deps
    data = payload.model_dump(exclude_unset=True)
    data["portfolio_id"] = portfolio_id  # enforce from path
    result = await create_uc.execute(ProgramCreate(**data))
    await session.commit()
    return result

@program_router.get("/portfolios/{portfolio_id}/programs", response_model=list[ProgramOut])
async def list_programs(portfolio_id: int, skip: int = 0, limit: int = Query(50, le=200), q: str | None = None, deps = Depends(get_usecases)):
    _, list_uc, *_ = deps
    return await list_uc.execute(portfolio_id, skip=skip, limit=limit, q=q)

@program_router.get("/programs/{program_id}", response_model=ProgramOut)
async def get_program(program_id: int, deps = Depends(get_usecases)):
    *_ , get_uc, _, _, _ = deps
    return await get_uc.execute(program_id)

@program_router.patch("/programs/{program_id}", response_model=ProgramOut)
async def update_program(program_id: int, payload: ProgramUpdate, deps = Depends(get_usecases)):
    *_ , update_uc, _, session = deps
    result = await update_uc.execute(program_id, payload)
    await session.commit()
    return result

@program_router.delete("/programs/{program_id}", response_model=ProgramOut)
async def delete_program(program_id: int, concurrency_guid: str, deps = Depends(get_usecases)):
    *_, delete_uc, session = deps
    result = await delete_uc.execute(program_id, concurrency_guid)
    await session.commit()
    return result
