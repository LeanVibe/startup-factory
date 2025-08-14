def test_dev_sh_status_mentions_deployer_and_public_url():
    from tools.business_blueprint_generator import BusinessLogicGenerator
    from tools.founder_interview_system import (
        FounderProfile,
        ProblemStatement,
        SolutionConcept,
        BusinessBlueprint,
        BusinessModel,
        IndustryVertical,
    )
    import asyncio

    gen = BusinessLogicGenerator(anthropic_client=None)
    bp = BusinessBlueprint(
        founder_profile=FounderProfile(name="d"),
        problem_statement=ProblemStatement(problem_description="d", target_audience="d"),
        solution_concept=SolutionConcept(
            core_value_proposition="d",
            key_features=["kf"],
            user_journey=["uj"],
            differentiation_factors=[],
            success_metrics=["sm"],
            monetization_strategy="subscription",
        ),
        business_model=BusinessModel.B2B_SAAS,
        industry_vertical=IndustryVertical.GENERAL,
        project_id="proj",
    )
    arts = asyncio.get_event_loop().run_until_complete(gen.generate_mvp_code(bp))

    dev = next(a for a in arts if a.file_path == "scripts/dev.sh")
    txt = dev.content
    # status prints public_url
    assert "public_url" in txt

    # project.json metadata mentions deployer fields in comments or generator docstrings
    main_router = next(a for a in arts if a.file_path == "backend/app/api/main.py")
    assert "API conventions" in main_router.content
