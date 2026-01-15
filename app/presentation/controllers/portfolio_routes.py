from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.presentation.schemas.portfolio_schema import PortfolioCreate, PortfolioUpdate, PortfolioOut
from app.core.db import get_session
from app.infrastructure.repositories.portfolio_repository_sqlalchemy import PortfolioRepository
from app.application.use_cases.portfolio.create_portfolio import CreatePortfolioUseCase
from app.application.use_cases.portfolio.list_portfolios import ListPortfoliosUseCase
from app.application.use_cases.portfolio.get_portfolio import GetPortfolioUseCase
from app.application.use_cases.portfolio.update_portfolio import UpdatePortfolioUseCase
from app.application.use_cases.portfolio.delete_portfolio import DeletePortfolioUseCase

portfolio_router = APIRouter(prefix="/portfolios", tags=["Portfolios"])

def get_usecases(session: AsyncSession = Depends(get_session)):
    repo = PortfolioRepository(session)
    return (
        CreatePortfolioUseCase(repo),
        ListPortfoliosUseCase(repo),
        GetPortfolioUseCase(repo),
        UpdatePortfolioUseCase(repo),
        DeletePortfolioUseCase(repo),
        session,
    )

@portfolio_router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
async def create_portfolio(payload: PortfolioCreate, deps = Depends(get_usecases)):
    create_uc, *_ , session = deps
    result = await create_uc.execute(payload)
    await session.commit()
    return result

@portfolio_router.get("", response_model=list[PortfolioOut])
async def list_portfolios(skip: int = 0, limit: int = Query(50, le=200), q: str | None = None, deps = Depends(get_usecases)):
    _, list_uc, *_ = deps
    return await list_uc.execute(skip=skip, limit=limit, q=q)

@portfolio_router.get("/{portfolio_id}", response_model=PortfolioOut)
async def get_portfolio(portfolio_id: int, deps = Depends(get_usecases)):
    *_ , get_uc, _, _, _ = deps
    return await get_uc.execute(portfolio_id)

@portfolio_router.patch("/{portfolio_id}", response_model=PortfolioOut)
async def update_portfolio(portfolio_id: int, payload: PortfolioUpdate, deps = Depends(get_usecases)):
    *_ , update_uc, _, session = deps
    result = await update_uc.execute(portfolio_id, payload)
    await session.commit()
    return result

@portfolio_router.delete("/{portfolio_id}", response_model=PortfolioOut)
async def delete_portfolio(portfolio_id: int, concurrency_guid: str, deps = Depends(get_usecases)):
    *_, delete_uc, session = deps
    result = await delete_uc.execute(portfolio_id, concurrency_guid)
    await session.commit()
    return result